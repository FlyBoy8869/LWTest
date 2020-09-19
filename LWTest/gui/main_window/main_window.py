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
import linewatchshared
from LWTest import sensor
from LWTest.collector import configure
from LWTest.collector.read.read import DataReader, PersistenceComparator, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.common.flags.flags import flags, FlagsEnum
from LWTest.constants import lwt
from LWTest.gui.createset.createsetdialog import manual_set_entry
from LWTest.gui.dialogs import PersistenceBootMonitor, CountDownDialog, UpgradeDialog, \
    SaveDataDialog, SpinDialog
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.gui.main_window.tablemodelview import SensorTableViewUpdater
from LWTest.gui.reference.referencedialog import ReferenceDialog
from LWTest.gui.widgets import LWTTableWidget
from LWTest.serial import ConfigureSerialNumbers
from LWTest.spreadsheet import spreadsheet
from LWTest.utilities import misc, file_utils
from LWTest.workers import upgrade, link
from linewatchshared.oscomp import QSettingsAdapter

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
        self.settings = QSettings()
        # self.resize(int(self.settings.value("geometry/mainwindow/width", "435")),
        #             int(self.settings.value("geometry/mainwindow/height", "244")))
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

        self.lock = QReadWriteLock()

        self.browser: Optional[webdriver.Chrome] = None

        self.spreadsheet_file_name: str = ""
        self.room_temp: QDoubleSpinBox = QDoubleSpinBox(self)

        self.changes = linewatchshared.changetracker.ChangeTracker()

        self.panel = QWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setLayout(self.panel_layout)

        # Menu Stuff
        self.menu_bar = self.menuBar()
        self.menu_helper = MenuHelper(self.menu_bar).create_menus(self)
        self.menu_helper.action_create_set.triggered.connect(self._manual_set_entry)
        self.menu_helper.action_create_set.setShortcut(Qt.Key_N | Qt.ControlModifier)

        self.menu_helper.action_enter_references.triggered.connect(self._enter_references)
        self.menu_helper.action_enter_references.setShortcut(Qt.Key_R | Qt.ControlModifier)

        self.menu_helper.action_upgrade.setShortcut(Qt.Key_U | Qt.ControlModifier)

        self.menu_helper.action_about.triggered.connect(lambda: menu_help_about_handler(parent=self))
        # end of Menu Stuff

        self.sensor_table = LWTTableWidget(self.panel)
        self.sensor_table.signals.double_clicked.connect(self._table_item_double_clicked)
        self.sensor_table.setAlternatingRowColors(True)
        self.sensor_table.setPalette(theme.sensor_table_palette)
        self.panel_layout.addWidget(self.sensor_table)

        self._table_view_updater = SensorTableViewUpdater(self.sensor_table, lambda: self.sensor_log.room_temperature)

        self._create_toolbar()

        self.signals.file_dropped.connect(lambda filename: print(f"dropped filename: {filename}"))
        self.signals.file_dropped.connect(lambda filename: self._handle_dropped_file(filename, self.sensor_log))
        self.signals.serial_numbers_imported.connect(self.sensor_log.append_all)

        self.setCentralWidget(self.panel)
        self.show()

    def closeEvent(self, closing_event: QCloseEvent):
        self.thread_pool.clear()

        if self.changes.can_discard(self):
            self._close_browser()

            width = self.width()
            height = self.height()
            self.settings.setValue("geometry/mainwindow/width", width)
            self.settings.setValue("geometry/mainwindow/height", height)

            closing_event.accept()
        else:
            closing_event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            filename = event.mimeData().urls()[0].toLocalFile()
            self.signals.file_dropped.emit(filename)
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_N and event.modifiers() == Qt.ControlModifier:
            self._manual_set_entry()
        elif event.key() == Qt.Key_R and event.modifiers() == Qt.ControlModifier:
            self._enter_references()
        else:
            super().keyReleaseEvent(event)

    def _manual_set_entry(self):
        if path := manual_set_entry(self):
            self.signals.file_dropped.emit(path)

    def _enter_references(self):
        reference_dialog = ReferenceDialog(self, self.high_voltage_reference, self.low_voltage_reference)
        reference_dialog.exec()
        self.high_voltage_reference = reference_dialog.high_voltage_reference
        self.low_voltage_reference = reference_dialog.low_voltage_reference

    def _handle_dropped_file(self, filename: str, sensor_log):
        # listens for MainWindow().signals.file_dropped
        if self._import_serial_numbers_from_spreadsheet(filename, sensor_log):
            self.spreadsheet_file_name = self._rename_dropped_file_to_atp_standard_file_name(
                filename,
                sensor_log.get_serial_numbers_as_tuple()
            )
            self._setup_sensor_table()
            self.changes.clear_change_flag()
            self.collector_configured = False

    def _import_serial_numbers_from_spreadsheet(self, filename: str, sensor_log) -> bool:
        if self.changes.can_discard(self):
            sensor_log.append_all(spreadsheet.get_serial_numbers(filename))
            return True

        return False

    @staticmethod
    def _rename_dropped_file_to_atp_standard_file_name(filename: str, serial_numbers: Tuple[str, ...]) -> str:
        new_file_path = file_utils.create_new_file_path(filename, serial_numbers)
        spreadsheet_path = Path(filename)
        return spreadsheet_path.rename(new_file_path.as_posix()).as_posix()

    def _setup_sensor_table(self):
        sensortable.setup_table_widget(self, self.sensor_log.get_serial_numbers_as_tuple(), self.sensor_table,
                                       self._manually_override_calibration_result,
                                       self._manually_override_fault_current_result)

        self._table_view_updater.update_from_model(self.sensor_log.get_sensors())

    @flags(set_=[FlagsEnum.SERIALS])
    def _configure_collector_serial_numbers(self):
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
        # pop dialog
        # load modem status page
        # scan page for linked sensors
        #   extract serial number and rssi
        #   save them
        # sleep for a bit
        # repeat until timeout
        dialog = SpinDialog(self, "Collecting startup data...\t\t\t", 0)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        link_thread = link.LinkWorker(self.sensor_log.get_serial_numbers_as_tuple(), lwt.URL_MODEM_STATUS)
        link_thread.signals.successful_link.connect(lambda d: self.sensor_log.record_rssi_readings(d[0], d[1]))
        link_thread.signals.successful_link.connect(lambda d: self._get_sensor_link_data(d[0]))
        link_thread.signals.link_timeout.connect(lambda nls: self.sensor_log.record_non_linked_sensors(nls))
        link_thread.signals.finished.connect(lambda: dialog.done(QDialog.Accepted))
        link_thread.signals.finished.connect(
            lambda: self._table_view_updater.update_from_model(self.sensor_log.get_sensors())
        )
        self.thread_pool.start(link_thread)

    def _upgrade_sensor(self, row: int):
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
        result = QMessageBox.warning(QMessageBox(self), LWTest.app_title, "Failed to upgrade sensor.",
                                     QMessageBox.Retry | QMessageBox.Cancel)

        self.firmware_upgrade_in_progress = False

        if result == QMessageBox.Retry:
            self._upgrade_sensor(row)

    @flags(read=[FlagsEnum.SERIALS], set_=[FlagsEnum.ADVANCED])
    def _do_advanced_configuration(self):
        self._get_browser()
        length = len(self.sensor_log)
        configure.do_advanced_configuration(length, self._get_browser(), QSettings())

    def _table_item_double_clicked(self, row: int):
        driver: webdriver.Chrome = self._get_browser()
        driver.get(lwt.URL_CALIBRATE)
        driver.find_elements_by_css_selector("option")[row].click()
        driver.find_element_by_css_selector("input[type='password']").send_keys("Q854Xj8X")
        driver.find_element_by_css_selector("input[type='submit']").click()

    def _start_calibration(self):
        utilities.misc.get_page_login_if_needed(lwt.URL_CALIBRATE, self._get_browser(), "calibration")

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED], set_=[FlagsEnum.CORRECTION])
    def _config_correction_angle(self):
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

    def _load_fault_current_page(self):
        self._get_browser().get(lwt.URL_FAULT_CURRENT)

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED, FlagsEnum.CORRECTION])
    def _take_readings(self):
        data_reader = DataReader(lwt.URL_SENSOR_DATA, lwt.URL_RAW_CONFIGURATION)
        data_reader.signals.high_data_readings.connect(self._process_high_data_readings)
        data_reader.signals.low_data_readings.connect(self._process_low_data_readings)
        data_reader.signals.page_load_error.connect(self._handle_take_readings_page_load_error)
        data_reader.read(self._get_browser(), self._get_sensor_count())

        self.changes.set_change_flag()

    def _handle_take_readings_page_load_error(self):
        self._show_information_dialog("Unable to retrieve readings. Check the collector.")

    def _process_high_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power."""

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

    def _manually_override_calibration_result(self, result, index):
        self.sensor_log.get_sensor_by_phase(index).calibrated = result

    def _manually_override_fault_current_result(self, result, index):
        self.sensor_log.get_sensor_by_phase(index).fault_current = result

    def _handle_persistence_boot_monitor_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._verify_raw_configuration_readings_persist()

    def _wait_for_collector_to_boot(self):
        pbm = PersistenceBootMonitor(self, self.thread_pool)
        pbm.finished.connect(self._handle_persistence_boot_monitor_finished_signal)
        pbm.open()

    def _handle_persistence_countdown_dialog_finished_signal(self, result_code):
        if result_code == QDialog.Accepted:
            self._show_information_dialog("Plug in the collector.\nClick 'OK' when ready.")
            self._wait_for_collector_to_boot()

    def _start_persistence_test(self):
        self._show_information_dialog("Unplug the collector.\nClick 'OK' when ready to proceed.")

        td = CountDownDialog(self, "Persistence",
                             "Please, wait before powering on the collector.\n" +
                             "'Cancel' will abort test.\t\t",
                             lwt.TimeOut.COLLECTOR_POWER_OFF_TIME.value)
        td.finished.connect(self._handle_persistence_countdown_dialog_finished_signal)
        td.open()

    def _save_data(self):
        if not all(self.high_voltage_reference) or not all(self.low_voltage_reference):
            self._enter_references()

        log_file_path = file_utils.create_log_filename(
            self.spreadsheet_file_name, self.sensor_log.get_serial_numbers_as_tuple()
        )
        save_data_dialog = SaveDataDialog(self, self.spreadsheet_file_name, log_file_path, iter(self.sensor_log),
                                          (self.sensor_log.room_temperature, self.high_voltage_reference, self.low_voltage_reference))
        result = save_data_dialog.exec()

        if result == QDialog.Accepted:
            self.changes.clear_change_flag()

    def _create_toolbar(self):
        toolbar = QToolBar("ToolBar")
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)

        toolbar.addAction(self.menu_helper.action_configure)
        self.menu_helper.action_configure.setData(self._configure_collector_serial_numbers)
        self.menu_helper.action_configure.triggered.connect(self._action_router)

        self.menu_helper.action_upgrade.setData(lambda: self._upgrade_sensor(
            self.sensor_table.currentRow()))
        self.menu_helper.action_upgrade.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_advanced_configuration)
        self.menu_helper.action_advanced_configuration.setData(self._do_advanced_configuration)
        self.menu_helper.action_advanced_configuration.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_calibrate)
        self.menu_helper.action_calibrate.setData(self._start_calibration)
        self.menu_helper.action_calibrate.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_config_correction_angle)
        self.menu_helper.action_config_correction_angle.setData(self._config_correction_angle)
        self.menu_helper.action_config_correction_angle.triggered.connect(self._action_router)

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
        self.menu_helper.action_take_readings.setData(self._take_readings)
        self.menu_helper.action_take_readings.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_check_persistence)
        self.menu_helper.action_check_persistence.setData(self._start_persistence_test)
        self.menu_helper.action_check_persistence.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_fault_current)
        self.menu_helper.action_fault_current.setData(self._load_fault_current_page)
        self.menu_helper.action_fault_current.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_save)
        self.menu_helper.action_save.setData(self._save_data)
        self.menu_helper.action_save.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)
        toolbar.addAction(self.menu_helper.action_exit)

    def _action_router(self):
        if self.sensor_log.is_empty():
            return

        if self.sender() is not None:
            self.sender().data()()

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

    def _set_sensor_table_widget_item_background(self, color: QBrush, row: int, col: int):
        item: QTableWidgetItem = self.sensor_table.item(row, col)
        item.setBackground(color)

    def _start_worker(self, worker):
        self.thread_pool.start(worker)

    def _show_information_dialog(self, message):
        QMessageBox.information(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)

    def _show_warning_dialog(self, message):
        QMessageBox.warning(self, LWTest.app_title, message, QMessageBox.Ok, QMessageBox.Ok)
