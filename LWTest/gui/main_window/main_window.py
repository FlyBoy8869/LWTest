from functools import partial
from typing import Optional

from PyQt5.QtCore import QThreadPool, QSettings, QSize, Qt, QReadWriteLock, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QDoubleSpinBox
from selenium import webdriver

import LWTest
import LWTest.constants.LWTConstants as LWT
import LWTest.gui.main_window.sensortable as sensortable
import LWTest.gui.theme as theme
import LWTest.utilities as utilities
import LWTest.utilities.misc as utilities_misc
import LWTest.validate as validator
from LWTest import sensor, common
from LWTest.collector import configure
from LWTest.collector.read.read import DataReader, PersistenceReader, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.common.flags.flags import flags, FlagsEnum
from LWTest.common.oscomp import QSettingsAdapter
from LWTest.gui.dialogs import PersistenceBootMonitor, CountDownDialog, UpgradeDialog, \
    SaveDataDialog, SpinDialog
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.serial import ConfigureSerialNumbers
from LWTest.spreadsheet import spreadsheet
from LWTest.utilities import misc
from LWTest.workers import upgrade, link
from LWTest.workers.persistence import PersistenceWorker

style_sheet = "QProgressBar{ max-height: 10px; }"

_DATA_IN_TABLE_ORDER = ("rssi", "firmware_version", "reporting_data", "calibrated", "high_voltage", "high_current",
                        "high_power_factor", "high_real_power", "low_voltage", "low_current",
                        "low_power_factor", "low_real_power", "scale_current", "scale_voltage",
                        "correction_angle", "persists", "temperature", "fault_current")

_DATA_IN_SPREADSHEET_ORDER = ("high_voltage", "high_current", "high_power_factor", "high_real_power",
                              "low_voltage", "low_current", "low_power_factor", "low_real_power",
                              "scale_current", "scale_voltage", "correction_angle", "persists",
                              "firmware_version", "reporting_data", "rssi", "calibrated",
                              "temperature", "fault_current")


class CellLocation:
    def __init__(self, row: int, col: int):
        if row < 0:
            raise ValueError(f"value {row} given for row must be 0 or greater")

        if col < 0:
            raise ValueError(f"value {col} given for col must be 0 or greater")

        self._row = row
        self._col = col

    @property
    def row(self):
        return self._row

    @property
    def col(self):
        return self._col


class MainWindow(QMainWindow):
    class Signals(QObject):
        file_dropped = pyqtSignal(str)
        adjust_size = pyqtSignal()
        serial_numbers_imported = pyqtSignal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.settings = QSettings()
        self.resize(int(self.settings.value("geometry/mainwindow/width", "435")),
                    int(self.settings.value("geometry/mainwindow/height", "244")))
        self.setWindowIcon(QIcon("LWTest/resources/images/app_128.png"))
        self.setWindowTitle(LWTest.app_title)
        self.setAcceptDrops(True)
        # self.setStyleSheet(style_sheet)

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

        self.spreadsheet_path: str = ""
        self.room_temp: QDoubleSpinBox = QDoubleSpinBox(self)

        self.changes = common.changetracker.ChangeTracker()

        self.validator = validator.Validator(
            partial(self._set_sensor_table_widget_item_background, QBrush(QColor(Qt.transparent))),
            partial(self._set_sensor_table_widget_item_background, QBrush(QColor(255, 0, 0, 50)))
        )

        self.panel = QWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setLayout(self.panel_layout)

        self.menu_bar = self.menuBar()
        self.menu_helper = MenuHelper(self.menu_bar).create_menus(self)

        self.menu_helper.action_about.triggered.connect(lambda: menu_help_about_handler(parent=self))

        self.sensor_table = QTableWidget(self.panel)
        self.sensor_table.setAlternatingRowColors(True)
        self.sensor_table.setPalette(theme.sensor_table_palette)
        self.panel_layout.addWidget(self.sensor_table)

        self._create_toolbar()

        self.signals.file_dropped.connect(lambda filename: print(f"dropped filename: {filename}"))
        self.signals.file_dropped.connect(lambda filename: self._import_serial_numbers(filename, self.sensor_log))
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
            self.spreadsheet_path = filename
            self.signals.file_dropped.emit(filename)
        else:
            event.ignore()

    def _import_serial_numbers(self, filename: str, sensor_log):
        # listens for MainWindow().signals.file_dropped
        if self.changes.can_discard(self):
            sensor_log.append_all(spreadsheet.get_serial_numbers(filename))
            self._setup_sensor_table()
            self.changes.clear_change_flag()
            self.collector_configured = False

    def _setup_sensor_table(self):
        sensortable.setup_table_widget(self, self.sensor_log.get_serial_numbers_as_tuple(), self.sensor_table,
                                       self._manually_override_calibration_result,
                                       self._manually_override_fault_current_result)

        self._update_from_model()

    @flags(set_=[FlagsEnum.SERIALS])
    def _configure_collector_serial_numbers(self):
        configurator = ConfigureSerialNumbers(
            misc.ensure_six_numbers(self.sensor_log.get_serial_numbers_as_list()),
            QSettingsAdapter().value("main/config_password"),
            self._get_browser(),
            LWT.URL_CONFIGURATION
        )

        result = configurator.configure()
        if result:
            self._start_confirm_serial_update()
        else:
            self._handle_serial_number_configuration_failure()

    @flags(clear=[FlagsEnum.SERIALS])
    def _handle_serial_number_configuration_failure(self):
        self._show_warning_dialog(f"An error occurred trying to configure the collector." +
                                  "\n\nMake sure the ethernet cable is connected and the collector is powered on.")

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

        link_thread = link.LinkWorker(self.sensor_log.get_serial_numbers_as_tuple(), LWT.URL_MODEM_STATUS)
        link_thread.signals.successful_link.connect(lambda d: self.sensor_log.record_rssi_readings(d[0], d[1]))
        link_thread.signals.successful_link.connect(lambda d: self._get_sensor_link_data(d[0]))
        link_thread.signals.link_timeout.connect(lambda nls: self.sensor_log.record_non_linked_sensors(nls))
        link_thread.signals.finished.connect(lambda: dialog.done(QDialog.Accepted))
        link_thread.signals.finished.connect(self._update_from_model)
        self.thread_pool.start(link_thread)

    def _upgrade_sensor(self, row: int):
        if not self.firmware_upgrade_in_progress:
            self.firmware_upgrade_in_progress = True

            browser = self._get_browser()
            serial_number = self.sensor_table.item(row, LWT.TableColumn.SERIAL_NUMBER.value).text()

            worker = upgrade.UpgradeWorker(serial_number, LWT.URL_UPGRADE_LOG)
            worker.signals.upgrade_successful.connect(self._upgrade_successful)
            worker.signals.upgrade_failed_to_enter_program_mode.connect(
                lambda: self._failed_to_enter_program_mode(row))

            upgrade_dialog = UpgradeDialog(serial_number, row, worker, self._start_worker, browser, self)
            upgrade_dialog.exec_()

    def _upgrade_successful(self, serial_number):
        self.firmware_upgrade_in_progress = False
        self.sensor_log.record_firmware_version(serial_number, LWT.LATEST_FIRMWARE_VERSION_NUMBER)
        self._update_from_model()

        QMessageBox.information(QMessageBox(self), LWTest.app_title, "Sensor firmware successfully upgraded.",
                                QMessageBox.Ok)

    def _failed_to_enter_program_mode(self, row: int):
        result = QMessageBox.warning(QMessageBox(self), LWTest.app_title, "Failed to upgrade sensor.",
                                     QMessageBox.Retry | QMessageBox.Cancel)

        self.firmware_upgrade_in_progress = False

        if result == QMessageBox.Retry:
            self._upgrade_sensor(row)

    @flags(read=[FlagsEnum.SERIALS], set_=[FlagsEnum.ADVANCED])
    def _do_advanced_configuration(self):
        self._get_browser()
        configure.do_advanced_configuration(len(self.sensor_log), self._get_browser(), QSettings())

    def _start_calibration(self):
        utilities.misc.get_page_login_if_needed(LWT.URL_CALIBRATE, self._get_browser(), "calibration")

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED], set_=[FlagsEnum.CORRECTION])
    def _config_correction_angle(self):
        if configure.configure_correction_angle(len(self.sensor_log), LWT.URL_CONFIGURATION,
                                                self._get_browser(), QSettings()):
            return

        self._handle_correction_angle_failure()

    @flags(clear=[FlagsEnum.CORRECTION])
    def _handle_correction_angle_failure(self):
        self._show_information_dialog("An error occurred configuring the correction angle.")

    def _verify_raw_configuration_readings_persist(self):
        persistence = PersistenceReader(LWT.URL_RAW_CONFIGURATION,
                                        self._get_browser(),
                                        self.sensor_log.get_persistence_values_for_comparison())

        persistence.signals.data_persisted.connect(self.sensor_log.record_persistence_readings)
        persistence.signals.finished.connect(self._update_from_model)

        worker = PersistenceWorker(persistence)
        self.thread_pool.start(worker)

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
                             LWT.TimeOut.COLLECTOR_POWER_OFF_TIME.value)
        td.finished.connect(self._handle_persistence_countdown_dialog_finished_signal)
        td.open()

    def _create_reporting_reader(self, index, url, browser):
        reporting_reader = ReportingDataReader(index, url, browser)
        reporting_reader.signals.data_reporting_data.connect(self.sensor_log.record_reporting_data)
        return reporting_reader

    def _create_firmware_reader(self, index, serial_number, url, browser):
        firmware_reader = FirmwareVersionReader(index, url, browser)
        firmware_reader.signals.firmware_version.connect(
            lambda i, version: self.sensor_log.record_firmware_version(serial_number, version))
        return firmware_reader

    def _get_sensor_link_data_readers(self, index, serial_number):
        firmware_reader = self._create_firmware_reader(index, serial_number, LWT.URL_UPGRADE, self._get_browser())
        reporting_reader = self._create_reporting_reader(index, LWT.URL_SENSOR_DATA, self._get_browser())
        return firmware_reader, reporting_reader

    def _get_sensor_line_position(self, serial_number):
        return self.sensor_log[serial_number].line_position

    def _get_sensor_link_data(self, serial_number):
        # responds to LinkWorker.successful_link signal
        self.lock.lockForRead()
        readers = self._get_sensor_link_data_readers(self._get_sensor_line_position(serial_number), serial_number)
        readers[0].read()
        readers[1].read()
        self._update_from_model()
        self.lock.unlock()

    def _load_fault_current_page(self):
        self._get_browser().get(LWT.URL_FAULT_CURRENT)

    @flags(read=[FlagsEnum.SERIALS, FlagsEnum.ADVANCED, FlagsEnum.CORRECTION])
    def _take_readings(self):
        data_reader = DataReader(LWT.URL_SENSOR_DATA, LWT.URL_RAW_CONFIGURATION)
        data_reader.signals.high_data_readings.connect(self._process_high_data_readings)
        data_reader.signals.low_data_readings.connect(self._process_low_data_readings)
        data_reader.signals.page_load_error.connect(self._handle_take_readings_page_load_error)
        data_reader.read(self._get_browser(), self._get_sensor_count())

        self.changes.set_change_flag()

    def _handle_take_readings_page_load_error(self):
        self._show_information_dialog("Unable to retrieve readings. Check the collector.")

    def _process_high_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power."""

        self.sensor_log.record_high_voltage_readings(readings[LWT.VOLTAGE])
        self.sensor_log.record_high_current_readings(readings[LWT.CURRENT])
        self.sensor_log.record_high_power_factor_readings(readings[LWT.FACTORS])
        self.sensor_log.record_high_real_power_readings(readings[LWT.POWER])

        self._update_from_model()

        data_set = tuple(zip(readings[LWT.VOLTAGE], readings[LWT.CURRENT], readings[LWT.POWER]))
        self.validator.validate_high_voltage_readings(data_set)

    def _process_low_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power, scale current,
        scale voltage, correction angle, temperature."""

        self.sensor_log.record_low_voltage_readings(readings[LWT.VOLTAGE])
        self.sensor_log.record_low_current_readings(readings[LWT.CURRENT])
        self.sensor_log.record_low_power_factor_readings(readings[LWT.FACTORS])
        self.sensor_log.record_low_real_power_readings(readings[LWT.POWER])
        self.sensor_log.record_scale_current_readings(readings[LWT.SCALE_CURRENT])
        self.sensor_log.record_scale_voltage_readings(readings[LWT.SCALE_VOLTAGE])
        self.sensor_log.record_correction_angle_readings(readings[LWT.CORRECTION_ANGLE])
        self.sensor_log.record_temperature_readings(readings[LWT.TEMPERATURE])

        self._update_from_model()

        data_set = tuple(zip(readings[LWT.VOLTAGE], readings[LWT.CURRENT], readings[LWT.POWER]))
        self.validator.validate_low_voltage_readings(data_set)

        data_set = tuple(zip(readings[LWT.SCALE_CURRENT], readings[LWT.SCALE_VOLTAGE], readings[LWT.CORRECTION_ANGLE]))
        self.validator.validate_scale_n_angle_readings(data_set)

        self.validator.validate_temperature_readings(float(self.sensor_log.room_temperature), readings[LWT.TEMPERATURE])

        self.menu_helper.action_check_persistence.setEnabled(True)

    def _manually_override_calibration_result(self, result, index):
        self.sensor_log.get_sensor_by_line_position(index).calibrated = result

    def _manually_override_fault_current_result(self, result, index):
        self.sensor_log.get_sensor_by_line_position(index).fault_current = result

    def _save_data(self):
        save_data_dialog = SaveDataDialog(self, self.spreadsheet_path, iter(self.sensor_log),
                                          self.sensor_log.room_temperature)
        result = save_data_dialog.exec()

        if result == QDialog.Accepted:
            self.changes.clear_change_flag()

    def _update_from_model(self):
        for index, sensor in enumerate(self.sensor_log):
            for j in range(LWT.TableColumn.RSSI.value, LWT.TableColumn.FAULT_CURRENT.value + 1):

                if j == LWT.TableColumn.FAULT_CURRENT.value:
                    self._update_combo_box(CellLocation(index, LWT.TableColumn.FAULT_CURRENT.value),
                                           sensor.fault_current)
                elif j == LWT.TableColumn.CALIBRATION.value:
                    self._update_combo_box(CellLocation(index, LWT.TableColumn.CALIBRATION.value),
                                           sensor.calibrated)
                else:
                    self.sensor_table.item(index, j).setText(sensor.__getattribute__(_DATA_IN_TABLE_ORDER[j - 1]))

    def _update_combo_box(self, cell_location: CellLocation, text: str) -> None:
        def _determine_index(result: str) -> int:
            indexes = {"Pass": 1, "Fail": 2}
            return indexes.get(result, 0)

        self.sensor_table.cellWidget(cell_location.row, cell_location.col).setCurrentIndex(_determine_index(text))

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
            self.browser = webdriver.Chrome(executable_path=LWT.chromedriver_path)

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
