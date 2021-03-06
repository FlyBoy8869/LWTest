import logging
from pathlib import Path
from typing import Optional, Tuple

from PyQt5 import QtGui
from PyQt5.QtCore import QThreadPool, QSettings, QSize, Qt, QReadWriteLock, \
    QObject, pyqtSignal, QTimer, QMutex
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, \
    QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QDoubleSpinBox, QApplication
from selenium import webdriver

import LWTest
import LWTest.collector.configure.phaseangle
from LWTest import changetracker
from LWTest import sensor, save, getrefs, web
from LWTest.collector.common.constants import ReadingType
from LWTest.collector.configure import raw
from LWTest.collector.configure.serial import ConfigureSerialNumbers
from LWTest.collector.read.electric import DataReader
from LWTest.collector.read.operational import FirmwareVersionReader, \
    ReportingDataReader
from LWTest.collector.read.persistence import PersistenceComparator
from LWTest.collector.state.state import DateTimeSynchronizer, Power
from LWTest.common.flags.flags import flags, FlagsEnum
from LWTest.constants import lwt
from LWTest.dialogs.countdown import CountDownDialog
from LWTest.dialogs.createset import manual_set_entry
from LWTest.dialogs.persistence import PersistenceBootMonitorDialog
from LWTest.dialogs.rssi import RSSIDialog
from LWTest.dialogs.upgrade import UpgradeDialog
from LWTest.gui import theme
from LWTest.gui.main_window import sensortable
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.gui.main_window.tablemodelview import SensorTableViewUpdater
from LWTest.gui.widgets import LWTTableWidget
from LWTest.spreadsheet import spreadsheet
from LWTest.utilities import misc, file_utils
from LWTest.utilities.oscomp import QSettingsAdapter
from LWTest.web.interface.page import Page
from LWTest.workers import upgrade, link

_logger = logging.getLogger(__name__)

style_sheet = "QProgressBar{ max-height: 10px; }"

_DATA_IN_SPREADSHEET_ORDER = (
    "high_voltage", "high_current", "high_power_factor", "high_real_power",
    "low_voltage", "low_current", "low_power_factor", "low_real_power",
    "scale_current", "scale_voltage", "correction_angle", "persists",
    "firmware_version", "reporting_data", "rssi",
    "calibrated", "temperature", "fault_current"
)

_mutex = QMutex()


class MainWindow(QMainWindow):
    class Signals(QObject):
        file_dropped = pyqtSignal(str)
        adjust_size = pyqtSignal()
        serial_numbers_imported = pyqtSignal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.settings = QSettings()
        self.resize(1550, 335)
        x_pos = (QApplication.primaryScreen().geometry().width() - self.width()) // 2
        self.move(x_pos, 5)
        self.setWindowIcon(QIcon("LWTest/resources/images/app_128.png"))
        self.setWindowTitle(LWTest.app_title)
        self.setAcceptDrops(True)
        # self.setStyleSheet(style_sheet)

        self.signals = self.Signals()
        self.threads = []
        # self.thread_pool = QThreadPool.globalInstance()
        self.sensor_log = sensor.SensorLog()
        self.sensor_log.changed.connect(self._update_table)
        self.firmware_upgrade_in_progress = False
        self.link_activity_string = ""

        # flags
        self.collector_configured = False

        # used when getting readings after the sensor links
        self.lock = QReadWriteLock()

        self.browser: Optional[webdriver.Chrome] = None
        self.headless_driver: webdriver.Chrome = self._get_headless_browser()

        self.spreadsheet_file_name: str = ""
        self.room_temp: QDoubleSpinBox = QDoubleSpinBox(self)

        self.changes = changetracker.ChangeTracker()

        self.panel = QWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setLayout(self.panel_layout)

        # Menu Stuff
        self.menu_bar = self.menuBar()
        self.menu_helper = MenuHelper(self, self.menu_bar).create_menus(self)
        self.menu_helper.connect_actions()
        # end of Menu Stuff

        self.sensor_table = None
        self._setup_sensor_table()
        self._create_toolbar()

        self.signals.file_dropped.connect(
            lambda filename: self._handle_dropped_file(
                filename, self.sensor_log
            )
        )
        self.signals.serial_numbers_imported.connect(self.sensor_log.create_all)

        self.setCentralWidget(self.panel)

        self.sensor_link_timer = QTimer()
        self.sensor_link_check_end_time = None

        QTimer.singleShot(1500, self._startup)

    def _startup(self):
        # check to see if the collector is responsive
        mb = self._show_information_dialog("Searching for collector", button=False, open_=True)
        power = Power()
        while power.is_off:
            if QMessageBox.question(self,
                                    "Searching for collector...",
                                    "The collector appears to be offline.\n\n"
                                    "Check the following:\n"
                                    "  - ethernet cable is connected\n"
                                    "  - collector is plugged in\n\n"
                                    "When the collector is ready, click\n"
                                    "'OK' to try again or\n'Cancel' to exit program.",
                                    QMessageBox.Ok, QMessageBox.Cancel
                                    ) == QMessageBox.Cancel:
                mb.close()
                self.close()
                return
        mb.close()

        # verify data and time on the collector
        mb = self._show_information_dialog("Synchronizing Date and Time", button=False, open_=True)
        dv = DateTimeSynchronizer(lwt.URL_DATE_TIME, "Q854Xj8X")
        date = dv.sync_date_time(self.headless_driver)
        if date:
            self.statusBar().showMessage(f"Updated the collector date and time to {date}.", 5000)
        mb.close()

    def closeEvent(self, closing_event: QCloseEvent):
        if self.changes.can_discard(parent=self):
            self._close_browser()
            _logger.debug("program terminated")
            closing_event.accept()
        else:
            closing_event.ignore()

    def _handle_action_exit(self):
        self.close()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            filename = event.mimeData().urls()[0].toLocalFile()
            if filename.lower().endswith(".xlsm"):
                _logger.info(f"dropped file: {filename}")
                event.setDropAction(Qt.CopyAction)
                self.signals.file_dropped.emit(filename)
                event.accept()
            else:
                _logger.debug(f"file type not supported: {filename}")
                event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, evt: QtGui.QKeyEvent) -> None:
        if evt.key() == Qt.Key_N and evt.modifiers() == Qt.ControlModifier:
            self._handle_action_create_set()
        elif evt.key() == Qt.Key_R and evt.modifiers() == Qt.ControlModifier:
            self._handle_action_enter_references()
        else:
            super().keyReleaseEvent(evt)

    def _handle_action_create_set(self):
        if path := manual_set_entry(self):
            self.signals.file_dropped.emit(path)

    # listens for MainWindow().signals.file_dropped
    def _handle_dropped_file(self, filename: str, sensor_log):
        if self._import_serial_numbers_from_spreadsheet(filename, sensor_log):
            self.spreadsheet_file_name =\
                self._rename_dropped_file_to_atp_standard_filename(
                    Path(filename),
                    sensor_log.get_serial_numbers_as_tuple(),
                    _logger
                ).as_posix()
            self.changes.clear_change_flag()
            self.collector_configured = False

    def _handle_action_enter_references(self):
        ref_getter = getrefs.GetReferences(self, *self.sensor_log.references)
        self.sensor_log.references = ref_getter.get_references()

    def _import_serial_numbers_from_spreadsheet(self, filename: str, sensor_log) -> bool:
        if self.changes.can_discard(parent=self):
            serial_numbers = spreadsheet.get_serial_numbers(filename)
            sensor_log.create_all(serial_numbers)
            self._setup_sensor_table(rows=len(serial_numbers))
            self._update_table()
            return True

        return False

    @staticmethod
    def _rename_dropped_file_to_atp_standard_filename(
            filename: Path, serial_numbers: Tuple[str, ...], logger
    ) -> Path:
        logger.debug(f"received file: {filename}")
        new_path: Path = file_utils.create_atr_path(filename, serial_numbers)
        logger.debug(f"dropped file renamed to: {new_path}")

        return filename.rename(new_path.as_posix())

    def _setup_sensor_table(self, rows=6):
        if self.sensor_table:
            self.panel_layout.removeWidget(self.sensor_table)

        self.sensor_table = LWTTableWidget(self.panel)
        self.panel_layout.addWidget(self.sensor_table)
        self.sensor_table.signals.double_clicked.connect(
            self._table_item_double_clicked
        )
        self.sensor_table.setAlternatingRowColors(True)
        self.sensor_table.setPalette(theme.sensor_table_palette)
        self._table_view_updater = SensorTableViewUpdater(lambda: self.sensor_log.room_temperature)
        sensortable.setup_table(
            self,
            self.sensor_table,
            self._manually_override_calibration_result,
            self._manually_override_fault_current_result,
            rows
        )

    @flags(set_=[FlagsEnum.SERIALS])
    def _handle_action_configure_serial_numbers(self, _: bool):
        serial_numbers = self.sensor_log.get_serial_numbers_as_list()
        configurator = ConfigureSerialNumbers(
            misc.ensure_six_numbers(serial_numbers),
            QSettingsAdapter().value("main/config_password"),
            self.headless_driver,
            lwt.URL_CONFIGURATION
        )

        result, error_msg = configurator.configure()
        if result:
            QTimer.singleShot(0, lambda: self._start_serial_update_verifier(serial_numbers))
        else:
            self._handle_serial_number_configuration_failure(error_msg)

    @flags(clear=[FlagsEnum.SERIALS])
    def _handle_serial_number_configuration_failure(self, error_msg: str):
        self._show_warning_dialog(error_msg)

    def _start_serial_update_verifier(self, serial_numbers):
        _logger.info("starting serial number update verification")
        verifier = link.SerialNumberUpdateVerifier(serial_numbers)
        verifier.serial_numbers_updated.connect(
            self._serial_numbers_successfully_updated
        )
        verifier.timed_out.connect(
            lambda: self.statusBar().showMessage(
                "Timed out verifying serial number update.", 10000
            )
        )
        verifier.verify()
        _logger.info("finished serial number update verification")

    def _serial_numbers_successfully_updated(self):
        self.statusBar().showMessage("Serial Numbers Updated.", 5000)
        QTimer.singleShot(0, self._start_sensor_link_check)

    def _start_sensor_link_check(self):
        rssi_dialog = RSSIDialog(self, self.sensor_log)
        rssi_dialog.signals.update.connect(self._rssi_update)
        rssi_dialog.signals.finished.connect(lambda: QTimer.singleShot(0, self._get_sensor_link_data))
        rssi_dialog.open()

    def _rssi_update(self, value, reading_type, serial_number):
        self.sensor_log.save(value, reading_type, serial_number)
        self._update_table()

    def _handle_action_upgrade_sensor(self):
        phase = self.sensor_table.currentRow()

        if not self.firmware_upgrade_in_progress:
            self.firmware_upgrade_in_progress = True

            browser = self._get_browser()
            serial_number = self.sensor_log.get_sensor_by_phase(phase).serial_number

            worker = upgrade.UpgradeWorker(serial_number, lwt.URL_UPGRADE_LOG)
            worker.signals.upgrade_successful.connect(self._upgrade_successful)
            worker.signals.upgrade_failed_to_enter_program_mode.connect(
                self._failed_to_enter_program_mode
            )

            upgrade_dialog = UpgradeDialog(serial_number, phase, worker, self._start_worker, browser, self)
            upgrade_dialog.error.connect(self._handle_upgrade_error_signal)
            upgrade_dialog.exec()

    def _handle_upgrade_error_signal(self, error_message: str):
        self._show_warning_dialog(
            "<h3>Error loading Upgrade page</h3>" +
            "<hr />" +
            f"{error_message}." +
            "<hr /><br>" +
            "Insure the collector is powered on and the ethernet cable is connected."
        )
        self.firmware_upgrade_in_progress = False

    def _upgrade_successful(self, serial_number):
        self.firmware_upgrade_in_progress = False
        phase = self._get_sensor_phase(serial_number)
        self.sensor_log.record_firmware_version(phase, lwt.LATEST_FIRMWARE_VERSION_NUMBER)
        self._update_table()

        self._show_information_dialog("Sensor firmware successfully upgraded.")

    def _failed_to_enter_program_mode(self):
        QMessageBox.warning(
            self,
            LWTest.app_title,
            "Failed to upgrade sensor.",
            QMessageBox.Ok
        )
        self.firmware_upgrade_in_progress = False

    @flags(read=[FlagsEnum.SERIALS], set_=[FlagsEnum.ADVANCED])
    def _handle_action_advanced_configuration(self, _: bool):
        msg_box = self._show_information_dialog("Setting Advanced Config constants", button=False, open_=True)

        password = QSettings().value("main/config_password")
        submit_buttons = [
            web.interface.page.Submit.create_submit_button_for_temperature_config(password),
            web.interface.page.Submit.create_submit_button_for_raw_config(password),
            web.interface.page.Submit.create_submit_button_for_voltage_ride_through(password)
        ]
        raw.do_advanced_configuration(self.headless_driver, Page, submit_buttons)

        msg_box.close()

    def _handle_action_calibrate(self):
        # just brings you to the calibration page for convenience
        Page.get(lwt.URL_CALIBRATE, self._get_browser())

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED], set_=[FlagsEnum.CORRECTION])
    def _handle_action_config_correction_angle(self, _: bool):
        msg_box = self._show_information_dialog("Setting Correction Angle", button=False, open_=True)

        password = QSettings().value("main/config_password")
        submit_button = web.interface.page.Submit.create_submit_button_for_phase_angle(password)

        if LWTest.collector.configure.phaseangle.configure_phase_angle(
                lwt.URL_CONFIGURATION,
                self.headless_driver,
                Page,
                submit_button
        ):
            msg_box.close()
            return

        msg_box.close()
        self._handle_correction_angle_failure()

    @flags(clear=[FlagsEnum.CORRECTION])
    def _handle_correction_angle_failure(self):
        self._show_information_dialog(
            "An error occurred configuring the correction angle."
        )

    def _verify_raw_configuration_readings_persist(self):
        comparator = PersistenceComparator()
        comparator.persisted.connect(self.sensor_log.save)
        comparator.compare(
            self.sensor_log.get_advanced_readings(),
            lwt.URL_RAW_CONFIGURATION,
            self._get_browser()
        )

    def _create_reporting_reader(self):
        reporting_reader = ReportingDataReader()
        reporting_reader.update.connect(
            lambda phase, reporting: self.sensor_log.save(
                reporting,
                ReadingType.REPORTING,
                serial_number=self.sensor_log.get_sensor_by_phase(phase).serial_number
            )
        )
        _logger.debug("created reporting reader")
        return reporting_reader

    def _create_firmware_reader(self):
        firmware_reader = FirmwareVersionReader()
        firmware_reader.update.connect(
            lambda phase, version: self.sensor_log.save(
                version,
                ReadingType.FIRMWARE,
                serial_number=self.sensor_log.get_sensor_by_phase(phase).serial_number
            )
        )
        _logger.debug("created firmware reader")
        return firmware_reader

    def _get_sensor_link_data_readers(self):
        firmware_reader = self._create_firmware_reader()
        reporting_reader = self._create_reporting_reader()
        return firmware_reader, reporting_reader

    def _get_sensor_phase(self, serial_number):
        return self.sensor_log[serial_number].phase

    def _get_sensor_link_data(self):
        _logger.info("reading firmware versions and data reporting status")
        serial_numbers = self.sensor_log.linked
        driver = self.headless_driver
        readers = self._get_sensor_link_data_readers()

        for serial_number in serial_numbers:
            phase = self._get_sensor_phase(serial_number)
            for reader in readers:
                self._get_sensor_link_data_actual(phase, reader, driver)

        self._update_table()

    @staticmethod
    def _get_sensor_link_data_actual(phase: int, reader, driver: webdriver.Chrome):
        reader.read(phase, driver)

    def _handle_action_fault_current(self, _: bool):
        self._get_browser().get(lwt.URL_FAULT_CURRENT)

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED, FlagsEnum.CORRECTION])
    def _handle_action_take_readings(self, _: bool):
        data_reader = DataReader(lwt.URL_SENSOR_DATA, lwt.URL_RAW_CONFIGURATION)
        data_reader.readings.connect(self.sensor_log.save)
        data_reader.readings.connect(lambda values, kind: self._enable_persistence_check(kind))
        data_reader.page_load_error.connect(self._handle_take_readings_page_load_error)
        data_reader.read(self._get_browser())

        self.changes.set_change_flag()

    def _handle_take_readings_page_load_error(self):
        self._show_information_dialog("Unable to retrieve readings. Check the collector.")

    def _enable_persistence_check(self, reading_type: str):
        if reading_type == ReadingType.TEMPERATURE:
            self.menu_helper.action_check_persistence.setEnabled(True)

    def _close_browser(self):
        if self.browser:
            self.browser.quit()
            self.browser = None

    @staticmethod
    def _can_save(changes: changetracker.ChangeTracker):
        return changes.is_changes

    def _get_browser(self):
        if self.browser is None:
            screen_height = QApplication.primaryScreen().geometry().height()
            geometry = self.geometry()
            frame_geometry = self.frameGeometry()
            app_bottom = frame_geometry.bottom()
            browser_height = screen_height - app_bottom
            options = webdriver.ChromeOptions()
            options.add_argument(f"window-size={self.width()},{browser_height}")
            options.add_argument(f"window-position={geometry.x()},{frame_geometry.height() + 25}")
            self.browser = webdriver.Chrome(executable_path=LWTest.constants.CHROMEDRIVER_PATH, options=options)
            _logger.debug("created instance of webdriver.Chrome")

        return self.browser

    @staticmethod
    def _get_headless_browser():
        _logger.info("created headless driver")
        options = webdriver.ChromeOptions()
        options.add_argument("headless=True")
        return webdriver.Chrome(executable_path=LWTest.constants.CHROMEDRIVER_PATH, options=options)

    def _handle_action_about(self):
        menu_help_about_handler(parent=self)

    def _handle_action_check_persistence(self):
        self._show_information_dialog("Unplug the collector.\nClick 'OK' when ready to proceed.")

        td = CountDownDialog(self, "Persistence",
                             "Please, wait before powering on the collector.\n" +
                             "'Cancel' will abort test.\t\t",
                             lwt.TimeOut.COLLECTOR_POWER_OFF_TIME.value)
        td.finished.connect(self._handle_persistence_countdown_dialog_finished_signal)
        td.open()

    def _handle_action_save(self):
        if not self._can_save(self.changes):
            return

        refs = getrefs.GetReferences(self, *self.sensor_log.references)
        action = save.DataSaver(self, self.spreadsheet_file_name, self.sensor_log, refs)
        if action.save():
            self.changes.clear_change_flag()

    def _handle_persistence_boot_monitor_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._verify_raw_configuration_readings_persist()

    def _handle_persistence_countdown_dialog_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._show_information_dialog("Plug in the collector.\nClick 'OK' when ready.")
            self._wait_for_collector_to_boot()

    def _manually_override_calibration_result(self, result, index):
        serial_number = self.sensor_log.get_sensor_by_phase(index).serial_number
        self.sensor_log.save(result, ReadingType.CALIBRATED, serial_number=serial_number)
        self._update_table()

    def _manually_override_fault_current_result(self, result, index):
        serial_number = self.sensor_log.get_sensor_by_phase(index).serial_number
        self.sensor_log.save(result, ReadingType.FAULT_CURRENT, serial_number=serial_number)

    def _save_window_geometry_to_settings(self):
        self.settings.setValue("geometry/mainwindow/width", self.width())
        self.settings.setValue("geometry/mainwindow/height", self.height())

    def _set_sensor_table_widget_item_background(self, color: QBrush, row: int, col: int):
        item: QTableWidgetItem = self.sensor_table.item(row, col)
        item.setBackground(color)

    @staticmethod
    def _start_worker(worker):
        QThreadPool.globalInstance().start(worker)

    def _show_information_dialog(self, message, button=True, open_=False):
        # QMessageBox.information(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)

        if button:
            btn = QMessageBox.Ok
        else:
            btn = QMessageBox.NoButton

        msg_box = QMessageBox(QMessageBox.Information, "", message, btn, self)

        if open_:
            msg_box.open()
            return msg_box
        else:
            msg_box.exec()
            return None

    def _show_warning_dialog(self, message):
        QMessageBox.warning(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)

    def _table_item_double_clicked(self, row: int):
        # prevent a calibration cycle from being started for an un-linked sensor
        if not self.sensor_log.get_sensor_by_phase(row).reporting_data:
            return

        driver: webdriver.Chrome = self._get_browser()
        driver.get(lwt.URL_CALIBRATE)
        element = driver.find_elements_by_css_selector("option")[row]
        phase = element.get_attribute("textContent")
        element.click()
        driver.find_element_by_css_selector("input[type='password']").send_keys("Q854Xj8X")
        driver.find_element_by_css_selector("input[type='submit']").click()

        # ask user to indicate results of calibration cycle
        result = QMessageBox.question(
            self,
            f"{phase} Calibration Result",
            f"Did {phase} pass calibration?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )

        # record that result in the table
        result_map = {
            QMessageBox.Yes: lambda: self._manually_override_calibration_result("Pass", row),
            QMessageBox.No: lambda: self._manually_override_calibration_result("Fail", row),
            QMessageBox.Cancel: lambda: None
        }
        result_map[result]()

    def _update_table(self):
        _logger.info("updating table")
        self._table_view_updater.update_from_model(self.sensor_log.get_sensors(), self.sensor_table)
        _logger.info("finished updating table")

    def _wait_for_collector_to_boot(self):
        pbm = PersistenceBootMonitorDialog(self)
        pbm.finished.connect(self._handle_persistence_boot_monitor_finished_signal)
        pbm.open()

    def _create_toolbar(self):
        toolbar = QToolBar("ToolBar")
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)

        toolbar.addAction(self.menu_helper.action_configure_serial_numbers)
        toolbar.addAction(self.menu_helper.action_advanced_configuration)
        toolbar.addAction(self.menu_helper.action_calibrate)
        toolbar.addAction(self.menu_helper.action_config_correction_angle)

        self.menu_helper.insert_spacer(toolbar, self)

        self.room_temp.setMinimum(0.0)
        self.room_temp.setMaximum(99.9)
        self.room_temp.setDecimals(1)
        self.room_temp.setSingleStep(0.1)
        self.room_temp.setPrefix(" ")
        self.room_temp.setSuffix(" \u00BAC ")
        self.room_temp.setValue(21.7)
        self.room_temp.setToolTip("Enter room temperature.")
        def set_room_temp(t): self.sensor_log.room_temperature = t
        self.room_temp.valueChanged.connect(lambda v: set_room_temp(v))
        toolbar.addWidget(self.room_temp)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_take_readings)
        toolbar.addAction(self.menu_helper.action_check_persistence)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_fault_current)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_save)

        self.menu_helper.insert_spacer(toolbar, self)
        toolbar.addAction(self.menu_helper.action_exit)
