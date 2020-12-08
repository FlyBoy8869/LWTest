import logging

from PyQt5 import QtGui
from PyQt5.QtCore import QThreadPool, QSettings, QSize, Qt, QReadWriteLock, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QDoubleSpinBox, QApplication
from pathlib import Path
from selenium import webdriver
from typing import Optional, Tuple

import LWTest
import LWTest.gui.main_window.sensortable as sensortable
import LWTest.gui.theme as theme
import LWTest.utilities as utilities
import LWTest.utilities.misc as utilities_misc
import LWTest.changetracker as changetracker
from LWTest import sensor
from LWTest.collector import configure
from LWTest.collector.read.read import DataReader, PersistenceComparator, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.common.flags.flags import flags, FlagsEnum
from LWTest.constants import lwt
from LWTest.dialogs.createset import manual_set_entry
from LWTest.dialogs.spin import SpinDialog
from LWTest.dialogs.countdown import CountDownDialog
from LWTest.dialogs.persistence import PersistenceBootMonitorDialog
from LWTest.dialogs.upgrade import UpgradeDialog
from LWTest.dialogs.save import SaveDialog
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.gui.main_window.tablemodelview import SensorTableViewUpdater
from LWTest.gui.reference.referencedialog import ReferenceDialog
from LWTest.gui.widgets import LWTTableWidget
from LWTest.serial import ConfigureSerialNumbers
from LWTest.spreadsheet import spreadsheet
from LWTest.utilities import misc, file_utils
from LWTest.web.interface.login import Login, Credentials
from LWTest.workers import upgrade, link
from LWTest.utilities.oscomp import QSettingsAdapter

style_sheet = "QProgressBar{ max-height: 10px; }"

_DATA_IN_SPREADSHEET_ORDER = ("high_voltage", "high_current", "high_power_factor", "high_real_power",
                              "low_voltage", "low_current", "low_power_factor", "low_real_power",
                              "scale_current", "scale_voltage", "correction_angle", "persists",
                              "firmware_version", "reporting_data", "rssi", "calibrated",
                              "temperature", "fault_current")


class MainWindow(QMainWindow):
    class Signals(QObject):
        file_dropped = pyqtSignal(str)
        adjust_size = pyqtSignal()
        serial_numbers_imported = pyqtSignal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self._logger = logging.getLogger(__name__)
        self.settings = QSettings()
        self.resize(1505, 315)
        x_pos = (QApplication.primaryScreen().geometry().width() - self.width()) // 2
        self.setGeometry(x_pos, 5, self.width(), self.height())
        self.setWindowIcon(QIcon("LWTest/resources/images/app_128.png"))
        self.setWindowTitle(LWTest.app_title)
        self.setAcceptDrops(True)
        # self.setStyleSheet(style_sheet)

        self.high_voltage_reference = ("", "", "", "")
        self.low_voltage_reference = ("", "", "", "")

        self.signals = self.Signals()
        self.thread_pool = QThreadPool.globalInstance()
        print(f"using max threads: {self.thread_pool.maxThreadCount()}")
        self.sensor_log = sensor.SensorLog()
        self.firmware_upgrade_in_progress = False
        self.link_activity_string = ""

        # flags
        self.collector_configured = False

        # used when getting readings after the sensor links
        self.lock = QReadWriteLock()

        self.browser: Optional[webdriver.Chrome] = None

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

        self.sensor_table = LWTTableWidget(self.panel)
        self.sensor_table.signals.double_clicked.connect(self._table_item_double_clicked)
        self.sensor_table.setAlternatingRowColors(True)
        self.sensor_table.setPalette(theme.sensor_table_palette)
        self.panel_layout.addWidget(self.sensor_table)

        self._table_view_updater = SensorTableViewUpdater(self.sensor_table, lambda: self.sensor_log.room_temperature)

        self._create_toolbar()

        self.signals.file_dropped.connect(lambda filename: self._handle_dropped_file(filename, self.sensor_log))
        self.signals.serial_numbers_imported.connect(self.sensor_log.append_all)

        self.setCentralWidget(self.panel)

    def closeEvent(self, closing_event: QCloseEvent):
        if self.changes.can_discard(parent=self):
            self.thread_pool.clear()
            self._close_browser()
            self._save_window_geometry_to_settings()
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
                self._logger.debug(f"dropped file: {filename}")
                event.setDropAction(Qt.CopyAction)
                self.signals.file_dropped.emit(filename)
                event.accept()
            else:
                self._logger.debug(f"file type not supported: {filename}")
                event.ignore()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_N and event.modifiers() == Qt.ControlModifier:
            self._handle_action_create_set()
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
            self._handle_action_enter_references()
        else:
            super().keyReleaseEvent(event)

    def _handle_action_create_set(self):
        if path := manual_set_entry(self):
            self.signals.file_dropped.emit(path)

    def _handle_action_enter_references(self):
        reference_dialog = ReferenceDialog(self, self.high_voltage_reference, self.low_voltage_reference)
        reference_dialog.exec()
        self.high_voltage_reference = reference_dialog.high_voltage_reference
        self.low_voltage_reference = reference_dialog.low_voltage_reference

    def _handle_dropped_file(self, filename: str, sensor_log):
        # listens for MainWindow().signals.file_dropped
        if self._import_serial_numbers_from_spreadsheet(filename, sensor_log):
            self.spreadsheet_file_name = self._rename_dropped_file_to_atp_standard_filename(
                Path(filename),
                sensor_log.get_serial_numbers_as_tuple(),
                self._logger
            ).as_posix()
            self._setup_sensor_table()
            self.changes.clear_change_flag()
            self.collector_configured = False

    def _import_serial_numbers_from_spreadsheet(self, filename: str, sensor_log) -> bool:
        if self.changes.can_discard(parent=self):
            sensor_log.append_all(spreadsheet.get_serial_numbers(filename))
            return True

        return False

    @staticmethod
    def _rename_dropped_file_to_atp_standard_filename(filename: Path, serial_numbers: Tuple[str, ...], logger) -> Path:
        logger.debug(f"received file: {filename}")
        new_path: Path = file_utils.create_atr_path(filename, serial_numbers)
        logger.debug(f"dropped file renamed to: {new_path}")

        return filename.rename(new_path.as_posix())

    def _setup_sensor_table(self):
        sensortable.setup_table_widget(self, self.sensor_log.get_serial_numbers_as_tuple(), self.sensor_table,
                                       self._manually_override_calibration_result,
                                       self._manually_override_fault_current_result)

        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

    @flags(set_=[FlagsEnum.SERIALS])
    def _handle_action_configure_serial_numbers(self, _: bool):
        configurator = ConfigureSerialNumbers(
            misc.ensure_six_numbers(self.sensor_log.get_serial_numbers_as_list()),
            QSettingsAdapter().value("main/config_password"),
            self._get_browser(),
            lwt.URL_CONFIGURATION
        )

        result = configurator.configure()
        if result:
            self._start_confirm_serial_update()
        else:
            self._handle_serial_number_configuration_failure()

    @flags(clear=[FlagsEnum.SERIALS])
    def _handle_serial_number_configuration_failure(self):
        self._show_warning_dialog("<h3>Error Configuring Collector</h3>" +
                                  "<hr/><br/>" +
                                  "Insure the collector is powered on and the ethernet cable is connected.")

    def _start_confirm_serial_update(self):
        dialog = SpinDialog(self, "Collecting startup data...\t\t\t")
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        link_thread = link.LinkWorker(self.sensor_log.get_serial_numbers_as_list(), lwt.URL_MODEM_STATUS)
        link_thread.signals.successful_link.connect(lambda d: self.sensor_log.record_rssi_readings(d[0], d[1]))
        link_thread.signals.successful_link.connect(lambda d: self._get_sensor_link_data(d[0]))
        link_thread.signals.link_timeout.connect(lambda nls: self.sensor_log.record_non_linked_sensors(nls))
        link_thread.signals.finished.connect(lambda: dialog.done(QDialog.Accepted))
        link_thread.signals.finished.connect(
            lambda: self._table_view_updater.update_from_model(self.sensor_log.get_sensors())
        )
        self.thread_pool.start(link_thread)

    def _handle_action_upgrade_sensor(self):
        row = self.sensor_table.currentRow()

        if not self.firmware_upgrade_in_progress:
            self.firmware_upgrade_in_progress = True

            browser = self._get_browser()
            serial_number = self.sensor_log.get_sensor_by_phase(row).serial_number

            worker = upgrade.UpgradeWorker(serial_number, lwt.URL_UPGRADE_LOG)
            worker.signals.upgrade_successful.connect(self._upgrade_successful)
            worker.signals.upgrade_failed_to_enter_program_mode.connect(
                lambda: self._failed_to_enter_program_mode(row))

            upgrade_dialog = UpgradeDialog(serial_number, row, worker, self._start_worker, browser, self)
            upgrade_dialog.error.connect(self._handle_upgrade_error_signal)
            upgrade_dialog.exec_()

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
        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

        self._show_information_dialog("Sensor firmware successfully upgraded.")

    def _failed_to_enter_program_mode(self, row: int):
        QMessageBox.warning(QMessageBox(self), LWTest.app_title, "Failed to upgrade sensor.", QMessageBox.Ok)
        self.firmware_upgrade_in_progress = False

    @flags(read=[FlagsEnum.SERIALS], set_=[FlagsEnum.ADVANCED])
    def _handle_action_advanced_configuration(self, _: bool):
        driver = self._get_browser()
        count = len(self.sensor_log)
        login = Login()
        configure.do_advanced_configuration(count, driver, login, QSettings())

    def _handle_action_calibrate(self):
        # just brings you to the calibration page for convenience
        login = Login()
        login.login(lwt.URL_CALIBRATE, self._get_browser())

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED], set_=[FlagsEnum.CORRECTION])
    def _handle_action_config_correction_angle(self, _: bool):
        if configure.configure_correction_angle(len(self.sensor_log), lwt.URL_CONFIGURATION,
                                                self._get_browser(), QSettings()):
            return

        self._handle_correction_angle_failure()

    @flags(clear=[FlagsEnum.CORRECTION])
    def _handle_correction_angle_failure(self):
        self._show_information_dialog("An error occurred configuring the correction angle.")

    def _verify_raw_configuration_readings_persist(self):
        comparator = PersistenceComparator()
        comparator.signals.persisted.connect(self.sensor_log.record_persistence_readings)
        comparator.signals.finished.connect(
            lambda: self._table_view_updater.update_from_model(self.sensor_log.get_sensors())
        )
        comparator.compare(
            self.sensor_log.get_advanced_readings(),
            len(self.sensor_log),
            lwt.URL_RAW_CONFIGURATION,
            self._get_browser()
        )

    def _create_reporting_reader(self):
        reporting_reader = ReportingDataReader()
        reporting_reader.signals.reporting.connect(self.sensor_log.record_reporting_data)
        return reporting_reader

    def _create_firmware_reader(self):
        firmware_reader = FirmwareVersionReader()
        firmware_reader.signals.version.connect(
            lambda phase, version: self.sensor_log.record_firmware_version(phase, version))
        return firmware_reader

    def _get_sensor_link_data_readers(self):
        firmware_reader = self._create_firmware_reader()
        reporting_reader = self._create_reporting_reader()
        return firmware_reader, reporting_reader

    def _get_sensor_phase(self, serial_number):
        print(f"getting phase for {serial_number}")
        return self.sensor_log[serial_number].phase

    def _get_sensor_link_data(self, serial_number):
        # responds to LinkWorker.successful_link signal
        self.lock.lockForRead()

        phase = self._get_sensor_phase(serial_number)
        readers = self._get_sensor_link_data_readers()
        readers[0].read(
            phase,
            lwt.URL_SOFTWARE_UPGRADE,
            self._get_browser()
        )
        readers[1].read(
            phase,
            lwt.URL_SENSOR_DATA,
            self._get_browser()
        )
        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

        self.lock.unlock()

    def _handle_action_fault_current(self, _: bool):
        self._get_browser().get(lwt.URL_FAULT_CURRENT)

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED, FlagsEnum.CORRECTION])
    def _handle_action_take_readings(self, _: bool):
        data_reader = DataReader(lwt.URL_SENSOR_DATA, lwt.URL_RAW_CONFIGURATION)
        data_reader.signals.high_data_readings.connect(self._process_high_data_readings)
        data_reader.signals.low_data_readings.connect(self._process_low_data_readings)
        data_reader.signals.page_load_error.connect(self._handle_take_readings_page_load_error)
        data_reader.read(self._get_browser(), self._get_sensor_count())

        self.changes.set_change_flag()

    def _handle_take_readings_page_load_error(self):
        self._show_information_dialog("Unable to retrieve readings. Check the collector.")

    def _process_high_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, power factor, power."""

        self.sensor_log.record_high_voltage_readings(readings[lwt.VOLTAGE])
        self.sensor_log.record_high_current_readings(readings[lwt.CURRENT])
        self.sensor_log.record_high_power_factor_readings(readings[lwt.FACTORS])
        self.sensor_log.record_high_real_power_readings(readings[lwt.POWER])

        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

    def _process_low_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power, scale current,
        scale voltage, correction angle, temperature."""

        self.sensor_log.record_low_voltage_readings(readings[lwt.VOLTAGE])
        self.sensor_log.record_low_current_readings(readings[lwt.CURRENT])
        self.sensor_log.record_low_power_factor_readings(readings[lwt.FACTORS])
        self.sensor_log.record_low_real_power_readings(readings[lwt.POWER])
        self.sensor_log.record_scale_current_readings(readings[lwt.SCALE_CURRENT])
        self.sensor_log.record_scale_voltage_readings(readings[lwt.SCALE_VOLTAGE])
        self.sensor_log.record_correction_angle_readings(readings[lwt.CORRECTION_ANGLE])
        self.sensor_log.record_temperature_readings(readings[lwt.TEMPERATURE])

        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

        self.menu_helper.action_check_persistence.setEnabled(True)

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

    def _close_browser(self):
        if self.browser:
            self.browser.quit()
            self.browser = None

    def _get_browser(self):
        if self.browser is None:
            geometry = self.geometry()
            frame_geometry = self.frameGeometry()
            options = webdriver.ChromeOptions()
            options.add_argument(f"window-size={self.width()},830")
            options.add_argument(f"window-position={geometry.x()},{frame_geometry.height() + 25}")
            self.browser = webdriver.Chrome(executable_path=LWTest.constants.CHROMEDRIVER_PATH, options=options)

        return self.browser

    def _get_sensor_count(self):
        return len(self.sensor_log)

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
        if not all(self.high_voltage_reference) or not all(self.low_voltage_reference):
            self._handle_action_enter_references()

        log_file_path = file_utils.create_log_filename(
            self.spreadsheet_file_name, self.sensor_log.get_serial_numbers_as_tuple()
        )
        save_data_dialog = SaveDialog(self, self.spreadsheet_file_name, log_file_path, iter(self.sensor_log),
                                      (self.sensor_log.room_temperature,
                                       self.high_voltage_reference,
                                       self.low_voltage_reference)
                                      )
        result = save_data_dialog.exec()

        if result == QDialog.Accepted:
            self.changes.clear_change_flag()

    def _handle_persistence_boot_monitor_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._verify_raw_configuration_readings_persist()

    def _handle_persistence_countdown_dialog_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._show_information_dialog("Plug in the collector.\nClick 'OK' when ready.")
            self._wait_for_collector_to_boot()

    def _manually_override_calibration_result(self, result, index):
        self.sensor_log.get_sensor_by_phase(index).calibrated = result

    def _manually_override_fault_current_result(self, result, index):
        self.sensor_log.get_sensor_by_phase(index).fault_current = result

    def _save_window_geometry_to_settings(self):
        self.settings.setValue("geometry/mainwindow/width", self.width())
        self.settings.setValue("geometry/mainwindow/height", self.height())

    def _set_sensor_table_widget_item_background(self, color: QBrush, row: int, col: int):
        item: QTableWidgetItem = self.sensor_table.item(row, col)
        item.setBackground(color)

    def _start_worker(self, worker):
        self.thread_pool.start(worker)

    def _show_information_dialog(self, message):
        QMessageBox.information(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)

    def _show_warning_dialog(self, message):
        QMessageBox.warning(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)

    def _table_item_double_clicked(self, row: int):
        driver: webdriver.Chrome = self._get_browser()
        driver.get(lwt.URL_CALIBRATE)
        driver.find_elements_by_css_selector("option")[row].click()
        driver.find_element_by_css_selector("input[type='password']").send_keys("Q854Xj8X")
        driver.find_element_by_css_selector("input[type='submit']").click()

    def _wait_for_collector_to_boot(self):
        pbm = PersistenceBootMonitorDialog(self, self.thread_pool)
        pbm.finished.connect(self._handle_persistence_boot_monitor_finished_signal)
        pbm.open()
