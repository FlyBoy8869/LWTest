from functools import partial

from PyQt5.QtCore import QThreadPool, QSettings, QSize
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QDoubleSpinBox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

import LWTest.LWTConstants as LWT
import LWTest.gui.main_window.sensortable as sensortable
import LWTest.utilities as utilities
import LWTest.utilities.misc as utilities_misc
import LWTest.validators as validators
from LWTest import sensor, signals
from LWTest.collector import configure
from LWTest.collector.read.confirm import ConfirmSerialConfig
from LWTest.collector.read.read import DataReader, FaultCurrentReader, PersistenceReader, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.gui.dialogs import PersistenceBootMonitor, ConfirmSerialConfigDialog, CountDownDialog, UpgradeDialog
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.gui.main_window.tasks import link as link_task
from LWTest.spreadsheet import spreadsheet
from LWTest.spreadsheet.constants import phases, PhaseReadings
from LWTest.workers import upgrade
from LWTest.workers.fault import FaultCurrentWorker
from LWTest.workers.persistence import PersistenceWorker
from LWTest.workers.postlink import PostLinkCheckWorker
from LWTest.workers.readings import ReadingsWorker
from LWTest.workers.serial import configure_serial_numbers


service = Service(QSettings().value("drivers/chromedriver"))
service.start()

_DATA_IN_TABLE_ORDER = ("rssi", "firmware_version", "reporting_data", "calibrated", "high_voltage", "high_current",
                        "high_power_factor", "high_real_power", "low_voltage", "low_current",
                        "low_power_factor", "low_real_power", "scale_current", "scale_voltage",
                        "correction_angle", "persists", "temperature", "fault_current")

_DATA_IN_SPREADSHEET_ORDER = ("high_voltage", "high_current", "high_power_factor", "high_real_power",
                              "low_voltage", "low_current", "low_power_factor", "low_real_power",
                              "scale_current", "scale_voltage", "correction_angle", "persists",
                              "firmware_version", "reporting_data", "rssi", "calibrated",
                              "temperature", "fault_current")


def dialog_title():
    return "LWtest"


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.settings = QSettings()
        self.resize(int(self.settings.value("geometry/mainwindow/width", "435")),
                    int(self.settings.value("geometry/mainwindow/height", "244")))
        self.setWindowIcon(QIcon("LWTest/resources/images/app_128.png"))
        self.setWindowTitle("LWTest")
        self.setAcceptDrops(True)
        self.signals = signals.MainWindowSignals()
        self.thread_pool = QThreadPool()
        self.sensor_log = sensor.SensorLog()
        self.firmware_upgrade_in_progress = False
        self.link_activity_string = ""
        self.browser: webdriver.Chrome = None
        self.unsaved_test_results = False
        self.spreadsheet_path = None
        self.room_temp: QDoubleSpinBox = QDoubleSpinBox(self)
        self.pass_func = partial(self._set_sensor_table_field_background, QBrush(QColor(255, 255, 255, 255)))
        self.fail_func = partial(self._set_sensor_table_field_background, QBrush(QColor(255, 0, 0, 50)))

        self.panel = QWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setLayout(self.panel_layout)

        self.menu_bar = self.menuBar()
        self.menu_helper = MenuHelper(self.menu_bar).create_menus(self)

        self.menu_helper.action_about.triggered.connect(lambda: menu_help_about_handler(parent=self))

        self.sensor_table = QTableWidget(self.panel)
        self.panel_layout.addWidget(self.sensor_table)

        self._create_toolbar()
        self.setCentralWidget(self.panel)
        self.show()

        self.signals.file_dropped.connect(lambda data: print(f"dropped filename: {data}"))
        self.signals.file_dropped.connect(lambda filename: self._import_serial_numbers(filename, self.sensor_log))
        self.signals.serial_numbers_imported.connect(self.sensor_log.append_all)

        self.browser: webdriver.Chrome

        self.activateWindow()

    def closeEvent(self, closing_event: QCloseEvent):
        self.thread_pool.clear()

        if self._discard_test_results():
            self._close_browser()

            width = self.width()
            height = self.height()
            self.settings.setValue("geometry/mainwindow/width", width)
            self.settings.setValue("geometry/mainwindow/height", height)

            closing_event.accept()
        else:
            closing_event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("FileName"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        filename = event.mimeData().urls()[0].toLocalFile()
        self.spreadsheet_path = filename
        self.signals.file_dropped.emit(filename)

    def _discard_test_results(self, clear_flag=True):
        if self.unsaved_test_results:
            result = QMessageBox.question(QMessageBox(self), f"{dialog_title()} - Unsaved Test Results",
                                          "Discard results?\t\t\t\t",
                                          QMessageBox.Yes | QMessageBox.No,
                                          QMessageBox.No)

            if result == QMessageBox.No:
                return False

        if clear_flag:
            self.unsaved_test_results = False

        return True

    def _import_serial_numbers(self, filename: str, sensor_log):
        # listens for MainWindow().signals.file_dropped

        if self._discard_test_results():
            sensor_log.append_all(spreadsheet.get_serial_numbers(filename))
            self._setup_sensor_table()

        self.unsaved_test_results = False

    def _setup_sensor_table(self):
        print(f"room temperature = {self.sensor_log.room_temperature}")
        sensortable.setup_table_widget(self, self.sensor_log.get_serial_numbers(), self.sensor_table,
                                       self._manually_override_calibrated_result,
                                       self._manually_override_fault_current_result)

    def _configure_collector_serial_numbers(self):
        worker = configure_serial_numbers(self.sensor_log.get_serial_numbers(), self._get_browser())
        worker.signals.finished.connect(self.__start_confirm_serial_update)
        worker.signals.failed.connect(self._serial_config_failed)

        self.thread_pool.start(worker)

    def _serial_config_failed(self):
        button = QMessageBox.warning(self, "LWTest - Page Load Error\t\t\t\t\t\t\t\t",
                                     f"An error occurred trying to send the serial numbers to the collector.\n\n" +
                                     "Make sure the ethernet cable is connected and the collector is booted,\n" +
                                     "then click 'Ok' to retry or 'Cancel' to abort.",
                                     QMessageBox.Ok | QMessageBox.Cancel)

        if button == QMessageBox.Ok:
            print("retrying to config the collector")
            self._configure_collector_serial_numbers()

    def __start_confirm_serial_update(self):
        confirm_serial_config = ConfirmSerialConfig(self.sensor_log.get_serial_numbers(), LWT.URL_MODEM_STATUS)
        confirm_serial_config.signals.confirmed.connect(self._determine_link_status)

        confirm_dialog = ConfirmSerialConfigDialog(confirm_serial_config, self.thread_pool, self)
        confirm_dialog.exec_()

    def _determine_link_status(self):
        link_task.determine_link_status(self.sensor_log, self.sensor_table, self.thread_pool, self,
                                        self._record_rssi_readings)

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
        self._record_firmware_version(serial_number, LWT.LATEST_FIRMWARE_VERSION_NUMBER)
        self._update_from_model()

        QMessageBox.information(QMessageBox(self), dialog_title(), "Sensor firmware successfully upgraded.",
                                QMessageBox.Ok)

    def _failed_to_enter_program_mode(self, row: int):
        result = QMessageBox.warning(QMessageBox(self), dialog_title(), "Failed to upgrade sensor.",
                                     QMessageBox.Retry | QMessageBox.Cancel)

        self.firmware_upgrade_in_progress = False

        if result == QMessageBox.Retry:
            self._upgrade_sensor(row)

    def _do_advanced_configuration(self):
        self._get_browser()
        configure.do_advanced_configuration(self._get_browser(), QSettings())

    def _start_calibration(self):
        utilities.misc.get_page_login_if_needed(LWT.URL_CALIBRATE, self._get_browser(), "calibration")

    def _config_correction_angle(self):
        while True:
            result = configure.configure_correction_angle(LWT.URL_CONFIGURATION, self._get_browser(), QSettings())

            if result:
                button = QMessageBox.warning(QMessageBox(self), "LWTest - warning\t\t\t\t",
                                             "Error configuring correction angle.\n\n" +
                                             "Check the collector and then click 'Ok' to retry or 'Cancel' to abort.",
                                             QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

                if button == QMessageBox.Cancel:
                    break
            else:
                break

    def _check_persistence(self):
        QMessageBox.information(QMessageBox(self), "LWTest", "Unplug the collector.\nClick 'OK' when ready to proceed.",
                                QMessageBox.Ok)

        td = CountDownDialog(self, "Persistence",
                             "Please, wait before powering on the collector.\n" +
                             "'Cancel' will abort test.\t\t",
                             LWT.TimeOut.COLLECTOR_POWER_OFF_TIME.value)

        result = td.exec_()

        if result == QDialog.Accepted:

            QMessageBox.information(QMessageBox(self), "LWTest",
                                    "Plug in the collector.\nClick 'OK' when ready to proceed.",
                                    QMessageBox.Ok)

            cb = PersistenceBootMonitor(self)
            cb.exec_()

            persistence = PersistenceReader(LWT.URL_RAW_CONFIGURATION,
                                            self._get_browser(),
                                            self.sensor_log.get_persistence_values_for_comparison())

            persistence.signals.data_persisted.connect(self._record_persistence_readings)
            persistence.signals.finished.connect(self._update_from_model)

            worker = PersistenceWorker(persistence)
            self.thread_pool.start(worker)

    def _read_post_link_data(self, serial_number):
        index = self.sensor_log[serial_number].line_position

        firmware_reader = FirmwareVersionReader(index, LWT.URL_UPGRADE, self._get_browser())
        firmware_reader.signals.firmware_version.connect(
            lambda i, version: self._record_firmware_version(serial_number, version))

        reporting_reader = ReportingDataReader(index, LWT.URL_SENSOR_DATA, self._get_browser())
        reporting_reader.signals.data_reporting_data.connect(self._record_reporting_data)

        worker = PostLinkCheckWorker((firmware_reader, reporting_reader))
        worker.signals.finished.connect(self._update_from_model)

        self.thread_pool.start(worker)

    def _read_fault_current(self):
        fault_current = FaultCurrentReader(LWT.URL_FAULT_CURRENT, self._get_browser())
        fault_current.signals.data_fault_current.connect(self._record_fault_current_readings)
        fault_current.signals.finished.connect(self._update_from_model)

        worker = FaultCurrentWorker(fault_current)
        self.thread_pool.start(worker)

    def _take_readings(self):
        choice = QMessageBox.Ok
        voltage_level = self.menu_helper.action_read_hi_or_low_voltage.data()

        if voltage_level == '13800':
            choice = QMessageBox.warning(QMessageBox(self), "LWTest\t\t\t\t\t\t",
                                         "<b>Meter is set to read 13800 volts.</b><br/><br/>"
                                         "If this is correct, click <b>'Ok'</b>.<br/><br/>"
                                         "If not, click <b>'Cancel'</b>, then click the<br/>"
                                         "battery icon to change scale.",
                                         QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

        if choice == QMessageBox.Ok:
            data_reader = DataReader(LWT.URL_SENSOR_DATA,
                                     LWT.URL_RAW_CONFIGURATION,
                                     self._get_browser(), self._get_sensor_count(),
                                     self.menu_helper.action_read_hi_or_low_voltage.data())

            if voltage_level == "13800":
                data_reader.signals.high_data_readings.connect(self._receive_high_data_readings)
            else:
                data_reader.signals.low_data_readings.connect(self._receive_low_data_readings)

            worker = ReadingsWorker(data_reader)
            self.thread_pool.start(worker)

            if self.menu_helper.action_read_hi_or_low_voltage.data() == '7200':
                self.menu_helper.action_check_persistence.setEnabled(True)

            self.unsaved_test_results = True

    def _receive_high_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power."""

        self._record_high_voltage_readings(readings[LWT.VOLTAGE])
        self._record_high_current_readings(readings[LWT.CURRENT])
        self._record_high_power_factor_readings(readings[LWT.FACTORS])
        self._record_high_real_power_readings(readings[LWT.POWER])

        self._update_from_model()

        data_set = tuple(zip(readings[LWT.VOLTAGE], readings[LWT.CURRENT], readings[LWT.POWER]))
        validators.validate_high_voltage_readings(self.pass_func, self.fail_func, data_set)

    def _receive_low_data_readings(self, readings: tuple):
        """Receives data in the following order: voltage, current, factors, power, scale current,
        scale voltage, correction angle, temperature."""

        self._record_low_voltage_readings(readings[LWT.VOLTAGE])
        self._record_low_current_readings(readings[LWT.CURRENT])
        self._record_low_power_factor_readings(readings[LWT.FACTORS])
        self._record_low_real_power_readings(readings[LWT.POWER])
        self._record_scale_current_readings(readings[LWT.SCALE_CURRENT])
        self._record_scale_voltage_readings(readings[LWT.SCALE_VOLTAGE])
        self._record_correction_angle_readings(readings[LWT.CORRECTION_ANGLE])
        self._record_temperature_readings(readings[LWT.TEMPERATURE])

        self._update_from_model()

        data_set = tuple(zip(readings[LWT.VOLTAGE], readings[LWT.CURRENT], readings[LWT.POWER]))
        validators.validate_low_voltage_readings(self.pass_func, self.fail_func, data_set)

        data_set = tuple(zip(readings[LWT.SCALE_CURRENT], readings[LWT.SCALE_VOLTAGE], readings[LWT.CORRECTION_ANGLE]))
        validators.validate_scale_n_angle_readings(self.pass_func, self.fail_func, data_set)

        validators.validate_temperature_readings(self.pass_func, self.fail_func,
                                                 float(self.sensor_log.room_temperature),
                                                 readings[LWT.TEMPERATURE])

    def _manually_override_calibrated_result(self, result, index):
        self.sensor_log.get_sensor_by_line_position(index).calibrated = result

    def _manually_override_fault_current_result(self, result, index):
        self.sensor_log.get_sensor_by_line_position(index).fault_current = result

    def _record_rssi_readings(self, serial_number, rssi):
        self.sensor_log[serial_number].rssi = rssi

    def _record_firmware_version(self, serial_number, version):
        self.sensor_log[serial_number].firmware_version = version

    def _record_reporting_data(self, line_position, reporting):
        self.sensor_log.get_sensor_by_line_position(line_position).reporting_data = reporting

        if reporting == "Fail":
            for index in range(4, 19):
                if index == LWT.TableColumn.CALIBRATION or index == LWT.TableColumn.FAULT_CURRENT:
                    self.sensor_table.cellWidget(line_position, index).setCurrentIndex(3)
                else:
                    self.sensor_table.item(line_position, index).setText("NA")

    def _record_sensor_calibration(self, result, index):
        self.sensor_log.get_sensor_by_line_position(index).calibrated = result

    def _record_high_voltage_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.high_voltage = values[index].replace(',', '')

    def _record_high_current_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.high_current = values[index]

    def _record_high_power_factor_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.high_power_factor = values[index]

    def _record_high_real_power_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.high_real_power = values[index]

    def _record_low_voltage_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.low_voltage = values[index].replace(',', '')

    def _record_low_current_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.low_current = values[index]

    def _record_low_power_factor_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.low_power_factor = values[index]

    def _record_low_real_power_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.low_real_power = values[index]

    def _record_temperature_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.temperature = values[index]

    def _record_fault_current_readings(self, value: str):
        unit: sensor.Sensor

        for unit in self.sensor_log:
            if unit.linked:
                unit.fault_current = value

    def _record_scale_current_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.scale_current = values[index]

    def _record_scale_voltage_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.scale_voltage = values[index]

    def _record_correction_angle_readings(self, values: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.correction_angle = values[index]

    def _record_persistence_readings(self, value: list):
        unit: sensor.Sensor

        for index, unit in enumerate(self.sensor_log):
            if unit.linked:
                unit.persists = value[index]

    def _save_data_to_spreadsheet(self):
        data_sets = []
        data = []
        for index, unit in enumerate(self.sensor_log):
            for field in _DATA_IN_SPREADSHEET_ORDER:
                data.append(unit.__getattribute__(field))

            phase = PhaseReadings(*phases[index])
            data_to_save = zip(phase, data)
            dts = list(data_to_save)

            data_sets.append(dts)
            data = []

        spreadsheet.save_sensor_data(self.spreadsheet_path, data_sets, self.sensor_log.room_temperature)

        self.unsaved_test_results = False

    def _update_table_with_reading(self, location, content):
        if self.sensor_log.get_sensor_by_line_position(location[0]).linked:
            item: QTableWidgetItem = self.sensor_table.item(location[0], location[1])
            item.setText(content)

    def _update_from_model(self):
        for index, unit in enumerate(self.sensor_log):
            for j in range(LWT.TableColumn.RSSI, LWT.TableColumn.FAULT_CURRENT + 1):

                # handle fault current
                if unit.linked and j == LWT.TableColumn.FAULT_CURRENT:
                    fc = unit.fault_current
                    combo_index = 0
                    if fc == "Pass":
                        combo_index = 1
                    elif fc == "Fail":
                        combo_index = 2
                    self.sensor_table.cellWidget(index, j).setCurrentIndex(combo_index)
                elif unit.linked and j == LWT.TableColumn.CALIBRATION.value:
                    pass
                # update table widget with current data if unit linked
                # if not linked only update columns j == rssi or firmware version index
                elif unit.linked or j == LWT.TableColumn.RSSI or j == LWT.TableColumn.FIRMWARE\
                        or j == LWT.TableColumn.REPORTING:
                    self.sensor_table.item(index, j).setText(unit.__getattribute__(_DATA_IN_TABLE_ORDER[j - 1]))

        self.sensor_table.resizeColumnsToContents()

    def _create_toolbar(self):
        toolbar = QToolBar("ToolBar")
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)

        toolbar.addAction(self.menu_helper.action_configure)
        self.menu_helper.action_configure.setData(self._configure_collector_serial_numbers)
        self.menu_helper.action_configure.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_upgrade)
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

        toolbar.addAction(self.menu_helper.action_read_hi_or_low_voltage)

        toolbar.addAction(self.menu_helper.action_check_persistence)
        self.menu_helper.action_check_persistence.setData(self._check_persistence)
        self.menu_helper.action_check_persistence.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_fault_current)
        self.menu_helper.action_fault_current.setData(self._read_fault_current)
        self.menu_helper.action_fault_current.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_save)
        self.menu_helper.action_save.setData(self._save_data_to_spreadsheet)
        self.menu_helper.action_save.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)
        toolbar.addAction(self.menu_helper.action_exit)

    def _action_router(self):
        if self.sensor_log.is_empty():
            return

        if self.sender() is not None:
            self.sender().data()()

    def _check_all_sensors_upgraded(self):
        for unit in self.sensor_log:
            if unit.linked and unit.firmware_version != "0x75":
                return False

        return True

    def _close_browser(self):
        if self.browser:
            self.browser.quit()
            self.browser = None

    def _get_browser(self):
        if self.browser is None:
            # self._driver = webdriver.Chrome(executable_path=self.settings.value("drivers/chromedriver"))
            self.browser = webdriver.Remote(service.service_url)
            # self._driver.minimize_window()
            # self._driver = chrome_worker.get_browser()

        return self.browser

    def _get_sensor_count(self):
        return len(self.sensor_log)

    def _set_sensor_table_field_background(self, color: QBrush, row: int, col: int):
        item: QTableWidgetItem = self.sensor_table.item(row, col)
        item.setBackground(color)

    def _start_worker(self, worker):
        self.thread_pool.start(worker)
