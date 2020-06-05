from datetime import datetime
from functools import partial
from typing import Optional

from PyQt5.QtCore import QThreadPool, QSettings, QSize
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QDoubleSpinBox
from selenium import webdriver

import LWTest.LWTConstants as LWT
import LWTest.gui.main_window.sensortable as sensortable
import LWTest.utilities as utilities
import LWTest.utilities.misc as utilities_misc
import LWTest.validator as validator
from LWTest import sensor, signals
from LWTest.collector import configure
from LWTest.collector.read.confirm import ConfirmSerialConfig
from LWTest.collector.read.read import DataReader, FaultCurrentReader, PersistenceReader, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.gui.dialogs import PersistenceBootMonitor, ConfirmSerialConfigDialog, CountDownDialog, UpgradeDialog, \
    SaveDataDialog
from LWTest.gui.main_window.create_menus import MenuHelper
from LWTest.gui.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.gui.main_window.tasks import link as link_task
from LWTest.spreadsheet import spreadsheet
from LWTest.workers import upgrade
from LWTest.workers.fault import FaultCurrentWorker
from LWTest.workers.persistence import PersistenceWorker
from LWTest.workers.postlink import PostLinkCheckWorker
from LWTest.workers.serial import configure_serial_numbers

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

        self.validator = validator.Validator(
            partial(self._set_sensor_table_widget_item_background, QBrush(QColor(255, 255, 255, 255))),
            partial(self._set_sensor_table_widget_item_background, QBrush(QColor(255, 0, 0, 50)))
        )

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

        self.browser: Optional[webdriver.Chrome] = None

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
                                       self._manually_override_calibration_result,
                                       self._manually_override_fault_current_result)

        self._update_from_model()

    def _configure_collector_serial_numbers(self):
        worker = configure_serial_numbers(self.sensor_log.get_serial_numbers(), self._get_browser())
        worker.signals.finished.connect(self._start_confirm_serial_update)
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

    def _start_confirm_serial_update(self):
        confirm_serial_config = ConfirmSerialConfig(self.sensor_log.get_serial_numbers(), LWT.URL_MODEM_STATUS)
        confirm_serial_config.signals.confirmed.connect(self._determine_link_status)

        confirm_dialog = ConfirmSerialConfigDialog(confirm_serial_config, self.thread_pool, self)
        confirm_dialog.exec_()

    def _determine_link_status(self):
        link_task.determine_link_status(self.sensor_log, self.sensor_table, self.thread_pool, self,
                                        self.sensor_log.record_rssi_readings)

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
        configure.do_advanced_configuration(len(self.sensor_log), self._get_browser(), QSettings())

    def _start_calibration(self):
        utilities.misc.get_page_login_if_needed(LWT.URL_CALIBRATE, self._get_browser(), "calibration")

    def _config_correction_angle(self):
        while True:
            result = configure.configure_correction_angle(len(self.sensor_log), LWT.URL_CONFIGURATION,
                                                          self._get_browser(), QSettings())

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

            persistence.signals.data_persisted.connect(self.sensor_log.record_persistence_readings)
            persistence.signals.finished.connect(self._update_from_model)

            worker = PersistenceWorker(persistence)
            self.thread_pool.start(worker)

    def _read_post_link_data(self, serial_number):
        index = self.sensor_log[serial_number].line_position

        firmware_reader = FirmwareVersionReader(index, LWT.URL_UPGRADE, self._get_browser())
        firmware_reader.signals.firmware_version.connect(
            lambda i, version: self.sensor_log.record_firmware_version(serial_number, version))

        reporting_reader = ReportingDataReader(index, LWT.URL_SENSOR_DATA, self._get_browser())
        reporting_reader.signals.data_reporting_data.connect(self.sensor_log.record_reporting_data)

        worker = PostLinkCheckWorker((firmware_reader, reporting_reader))
        worker.signals.finished.connect(self._update_from_model)

        self.thread_pool.start(worker)

    def _read_fault_current(self):
        fault_current = FaultCurrentReader(LWT.URL_FAULT_CURRENT, self._get_browser())
        fault_current.signals.data_fault_current.connect(self.sensor_log.record_fault_current_readings)
        fault_current.signals.finished.connect(self._update_from_model)

        worker = FaultCurrentWorker(fault_current)
        self.thread_pool.start(worker)

    def _take_readings(self):
        data_reader = DataReader(LWT.URL_SENSOR_DATA, LWT.URL_RAW_CONFIGURATION)

        data_reader.signals.high_data_readings.connect(self._process_high_data_readings)
        data_reader.signals.low_data_readings.connect(self._process_low_data_readings)

        data_reader.read(self._get_browser(), self._get_sensor_count())

        self.unsaved_test_results = True

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
            self.unsaved_test_results = False

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

        self.sensor_table.resizeColumnsToContents()

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
        self.menu_helper.action_check_persistence.setData(self._check_persistence)
        self.menu_helper.action_check_persistence.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)

        toolbar.addAction(self.menu_helper.action_fault_current)
        self.menu_helper.action_fault_current.setData(self._read_fault_current)
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
            self.browser = webdriver.Chrome(executable_path=QSettings().value("drivers/chromedriver"))

        return self.browser

    def _get_sensor_count(self):
        return len(self.sensor_log)

    def _set_sensor_table_widget_item_background(self, color: QBrush, row: int, col: int):
        item: QTableWidgetItem = self.sensor_table.item(row, col)
        item.setBackground(color)

    def _start_worker(self, worker):
        self.thread_pool.start(worker)
