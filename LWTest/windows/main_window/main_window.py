import datetime
from time import sleep

from PyQt5.QtCore import QThreadPool, QSettings, Qt
from PyQt5.QtGui import QIcon, QCloseEvent, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar, \
    QDialog, QComboBox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

import LWTest.utilities as utilities
from LWTest import sensor, signals
from LWTest.collector import configure
from LWTest.collector.read.confirm import ConfirmSerialConfig
from LWTest.collector.read.read import DataReader, FaultCurrentReader, PersistenceReader, FirmwareVersionReader, \
    ReportingDataReader
from LWTest.config.app import logging as lwt_logging, settings as lwt_settings
from LWTest.config.dom import constants
from LWTest.spreadsheet import spreadsheet
from LWTest.spreadsheet.constants import phases, PhaseReadings
from LWTest.utilities.misc import create_item
from LWTest.windows.dialogs import PersistenceWaitDialog
from LWTest.windows.main_window.create_menus import MenuHelper
from LWTest.windows.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.windows.main_window.tasks import link as link_task
from LWTest.windows.main_window.tasks import serial as serial_task
from LWTest.workers import upgrade
from LWTest.workers.confirm import ConfirmSerialConfigWorker
from LWTest.workers.fault import FaultCurrentWorker
from LWTest.workers.persistence import PersistenceWorker
from LWTest.workers.postlink import PostLinkCheckWorker
from LWTest.workers.readings import ReadingsWorker

lwt_settings.load(r"LWTest/resources/config/config.txt")
lwt_logging.initialize()

service = Service(r"LWTest\resources\drivers\chromedriver\windows\version_78-0-3904-70\chromedriver.exe")
service.start()

_DATA_IN_TABLE_ORDER = ["rssi", "firmware_version", "reporting_data", "high_voltage", "high_current",
                        "high_power_factor", "high_real_power", "low_voltage", "low_current",
                        "low_power_factor", "low_real_power", "temperature", "fault_current",
                        "scale_current", "scale_voltage", "correction_angle", "persists"]

_DATA_IN_SPREADSHEET_ORDER = ["high_voltage", "high_current", "high_power_factor", "high_real_power",
                              "low_voltage", "low_current", "low_power_factor", "low_real_power",
                              "scale_current", "scale_voltage", "correction_angle", "persists",
                              "firmware_version", "reporting_data", "rssi", "temperature", "fault_current"]

_PERSISTENCE_TIMEOUT = 15


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

        self.panel = QWidget(self)
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel.setLayout(self.panel_layout)

        self.menu_bar = self.menuBar()
        self.menu_helper = MenuHelper(self.menu_bar).create_menus(self)

        self.menu_helper.action_about.triggered.connect(lambda: menu_help_about_handler(parent=self))

        self.qtw_sensors = QTableWidget(self.panel)
        self.panel_layout.addWidget(self.qtw_sensors)

        self._create_toolbar()
        self.setCentralWidget(self.panel)
        self.show()

        self.signals.file_dropped.connect(lambda data: print(f"dropped filename: {data}"))
        self.signals.file_dropped.connect(self._import_serial_numbers)
        self.signals.adjust_size.connect(self._resize_table)
        self.signals.serial_numbers_imported.connect(self.sensor_log.append_all)

        self.browser: webdriver.Chrome
        # misc.load_start_page(self.browser)
        # self.browser.maximize_window()

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
        self.signals.file_dropped.emit(event.mimeData().urls()[0].toLocalFile())

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

    def _import_serial_numbers(self, filename: str):

        if self._discard_test_results():
            self.spreadsheet_path = filename
            sn = spreadsheet.get_serial_numbers(filename)

            headers = ["Serial Number", "\t\t\t\t\t\tRSSI\t\t\t\t\t\t", "Firmware", "Reporting Data",
                       "\t\t\t\t\t\t13.8K\t\t\t\t\t\t", "\t\t\t\t120A\t\t\t\t", "Power Factor", "Real Power",
                       "\t\t\t\t\t\t7.2K\t\t\t\t\t\t", "\t\t\t\t\t60A\t\t\t\t\t", "Power Factor", "Real Power",
                       "Temperature", "Fault Current", "Scale Current", "Scale Voltage",
                       "Correction Angle", "\t\tPersists\t\t\t\t", "Calibration"]

            self.qtw_sensors.clear()
            self.qtw_sensors.setRowCount(len(sn))
            self.qtw_sensors.setColumnCount(len(headers))
            self.qtw_sensors.setHorizontalHeaderLabels(headers)

            for index, number in enumerate(sn):
                item = create_item(number)
                item.setFlags(item.flags() | Qt.ItemIsSelectable)
                self.qtw_sensors.setItem(index, 0, item)

                # for column in range(1, len(headers) - 1):
                for column in range(1, 13):
                    item = create_item()
                    self.qtw_sensors.setItem(index, column, item)

                fault_combo = QComboBox(self)
                fault_combo.insertItems(0, ["", "Pass", "Fail", "NA"])
                fault_combo.currentTextChanged.connect(
                    lambda text, index=index: self._manually_override_fault_current_result(text, index)
                )
                self.qtw_sensors.setCellWidget(index, 13, fault_combo)

                for column in range(14, 18):
                    item = create_item()
                    self.qtw_sensors.setItem(index, column, item)

                cal_combo = QComboBox(self)
                cal_combo.insertItems(0, [" ", "Pass", "Fail", "NA"])
                cal_combo.currentTextChanged.connect(
                    lambda text, index=index: self._record_sensor_calibration(text, index)
                )
                self.qtw_sensors.setCellWidget(index, 18, cal_combo)

            self.qtw_sensors.setCurrentCell(0, 0)
            self.qtw_sensors.resizeColumnsToContents()

            self.signals.adjust_size.emit()
            self.signals.serial_numbers_imported.emit(tuple(sn))

            self.menu_helper.action_check_persistence.setEnabled(False)
            self.unsaved_test_results = False

    def _resize_table(self):
        window_width = int(self.settings.value("geometry/mainwindow/width", "435"))
        window_height = int(self.settings.value("geometry/mainwindow/height", "244"))
        self.resize(window_width, window_height)

    def _resize_table_columns(self):
        self.qtw_sensors.resizeColumnsToContents()

    def _configure_collector_serial_numbers(self):
        serial_task.configure_serial_numbers(self.sensor_log.get_serial_numbers(),
                                             self._get_browser(),
                                             self, self.thread_pool, self._confirm_serial_update)

    def _confirm_serial_update(self):
        settings = QSettings()
        url = settings.value("pages/modem_status")
        serial_numbers = self.sensor_log.get_serial_numbers()

        confirm_serial_config = ConfirmSerialConfig(serial_numbers, url)
        confirm_serial_config.signals.confirmed.connect(self._enable_advanced_config_if_possible)
        confirm_serial_config.signals.confirmed.connect(self._determine_link_status)

        worker = ConfirmSerialConfigWorker(confirm_serial_config)

        self.thread_pool.start(worker)

    def _enable_advanced_config_if_possible(self):
        if self._check_all_sensors_upgraded():
            self.menu_helper.enable_actions(1)

    def _determine_link_status(self):
        link_task.determine_link_status(self.sensor_log, self.qtw_sensors, self.thread_pool, self,
                                        self._record_rssi_readings)

    def _upgrade_sensor_at_row_col(self, row: int, ignore_failures=False):
        if not self.firmware_upgrade_in_progress:
            settings = QSettings()
            self.firmware_upgrade_in_progress = True

            # start sensor firmware upgrade
            browser = self._get_browser()
            browser.get(settings.value('pages/software_upgrade'))
            if "Please reload after a moment" in browser.page_source:
                browser.get(settings.value('pages/software_upgrade'))

            browser.find_element_by_xpath(constants.unit_select_button[row]).click()
            browser.find_element_by_xpath(constants.firmware_file).send_keys(
                "LWTest/resources/firmware/firmware-0x0075.zip")
            browser.find_element_by_xpath(constants.upgrade_password).send_keys(settings.value('main/config_password'))
            browser.find_element_by_xpath(constants.upgrade_button).click()

            sleep(1)

            # date = datetime.datetime.now()
            # file = f"{date.year}-{date.month:02d}-{date.day:02d}_UPDATER.txt"
            # upgrade_log = f"http://192.168.2.1/index.php/log_viewer/view/{file}"
            upgrade_log = settings.value("pages/software_upgrade_log")

            worker = upgrade.UpgradeWorker(self.qtw_sensors.item(row, 0).text(),
                                           (row, 3),
                                           upgrade_log,
                                           ignore_failures=ignore_failures)
            worker.signals.upgrade_successful.connect(self._upgrade_successful)
            worker.signals.upgrade_timed_out.connect(self._upgrade_timed_out)
            worker.signals.upgrade_show_activity.connect(self._upgrade_show_activity)
            worker.signals.upgrade_failed_to_enter_program_mode.connect(self._failed_to_enter_program_mode)
            self.thread_pool.start(worker)

    def _upgrade_successful(self, serial_number):
        row = self.sensor_log[serial_number].line_position
        self._update_table_with_reading((row, 2), "0x75")
        self.firmware_upgrade_in_progress = False

        # self._enable_advanced_config_if_possible()

        QMessageBox.information(QMessageBox(self), dialog_title(), "Sensor firmware successfully upgraded.",
                                QMessageBox.Ok)

    def _failed_to_enter_program_mode(self, row: int):
        result = QMessageBox.warning(QMessageBox(self), dialog_title(), "Failed to enter program mode.",
                                     QMessageBox.Retry | QMessageBox.Cancel)

        self.firmware_upgrade_in_progress = False
        if result == QMessageBox.Retry:
            # row = self.sensor_log.get_line_position_of_sensor(serial_number)
            self._upgrade_sensor_at_row_col(row, ignore_failures=True)

    def _upgrade_show_activity(self, row: int):
        item: QTableWidgetItem = self.qtw_sensors.item(row, 2)
        if item.text().startswith("0x"):
            item.setText("")

        if len(item.text()) < 5:
            text = item.text() + "-"
            item.setText(text)
        else:
            item.setText("-")

    def _upgrade_timed_out(self, serial_number):
        self.firmware_upgrade_in_progress = False

        QMessageBox.warning(QMessageBox(self), f"{dialog_title()} - Upgrading Sensor", "Process timed out.\t\t",
                            QMessageBox.Ok)

    def _do_advanced_configuration(self):
        self._get_browser()
        count = self._get_sensor_count()
        configure.do_advanced_configuration(count, self._get_browser())

    def _start_calibration(self):
        settings = QSettings()
        url = settings.value("pages/calibration")

        browser = self._get_browser()
        utilities.misc.get_page_login_if_needed(url, browser, "calibration")

    def _config_correction_angle(self):
        settings = QSettings()

        while True:
            count = self._get_sensor_count()
            result = configure.configure_correction_angle(settings.value('pages/configuration'),
                                                          self._get_browser(),
                                                          count)

            if result:
                button = QMessageBox.warning(self, "LWTest - warning\t\t\t\t",
                                             "Error requesting Configuration page.\n\n" +
                                             "Check the collector and then click 'Ok' to retry request.",
                                             QMessageBox.Ok | QMessageBox.Cancel)
                if button == QMessageBox.Cancel:
                    break
            else:
                break

    def _check_persistence(self):
        settings = QSettings()

        QMessageBox.information(QMessageBox(self), "LWTest", "Unplug the collector.\nClick 'OK' when ready to proceed.",
                                QMessageBox.Ok)

        pd = PersistenceWaitDialog(self, "Persistence", "Please, wait before powering on the collector.\n" +
                                   "'Cancel' will abort test.\t\t", _PERSISTENCE_TIMEOUT)
        result = pd.exec_()

        if result == QDialog.Accepted:

            QMessageBox.information(QMessageBox(self), "LWTest",
                                    "Plug in the collector.\nClick 'OK' when ready to proceed.",
                                    QMessageBox.Ok)

            pd = PersistenceWaitDialog(self, "Persistence", "Please, wait for the collector to boot.\t\t",
                                       0, url=settings.value("pages/raw_configuration"))
            pd.exec_()

            persistence = PersistenceReader(settings.value("pages/raw_configuration"),
                                            self._get_browser(),
                                            self.qtw_sensors,
                                            self._get_sensor_count())

            persistence.signals.data_persisted.connect(self._record_persistence_readings)
            persistence.signals.finished.connect(self._update_from_model)

            worker = PersistenceWorker(persistence)
            self.thread_pool.start(worker)

    def _read_post_link_data(self, serial_number):
        settings = QSettings()
        index = self.sensor_log[serial_number].line_position

        firmware_reader = FirmwareVersionReader(index, settings.value('pages/software_upgrade'), self._get_browser())
        firmware_reader.signals.firmware_version.connect(
            lambda i, version: self._record_firmware_version(serial_number, version))

        reporting_reader = ReportingDataReader(index, settings.value("pages/sensor_data"), self._get_browser())
        reporting_reader.signals.data_reporting_data.connect(self._record_reporting_data)

        worker = PostLinkCheckWorker((firmware_reader, reporting_reader))
        worker.signals.finished.connect(self._update_from_model)
        worker.signals.finished.connect(self._enable_advanced_config_if_possible)

        self.thread_pool.start(worker)

    def _read_fault_current(self):
        settings = QSettings()

        fault_current = FaultCurrentReader(settings.value('pages/fault_current'), self._get_browser())
        fault_current.signals.data_fault_current.connect(self._record_fault_current_readings)
        fault_current.signals.finished.connect(self._update_from_model)

        worker = FaultCurrentWorker(fault_current)
        self.thread_pool.start(worker)

    def _take_readings(self):
        settings = QSettings()
        choice = QMessageBox.Ok

        if self.menu_helper.action_read_hi_or_low_voltage.data() == '13800':
            choice = QMessageBox.warning(QMessageBox(self), "LWTest\t\t\t\t\t\t",
                                         "<b>Meter is set to read 13800 volts.</b><br/><br/>"
                                         "If this is correct, click <b>'Ok'</b>.<br/><br/>"
                                         "If not, click <b>'Cancel'</b>, then click the<br/>"
                                         "battery icon to change scale.",
                                         QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

        if choice == QMessageBox.Ok:
            data = DataReader(settings.value('pages/sensor_data'),
                              settings.value('pages/raw_configuration'),
                              self._get_browser(), self._get_sensor_count(),
                              self.menu_helper.action_read_hi_or_low_voltage.data())

            data.signals.data_high_voltage.connect(self._record_high_voltage_readings)
            data.signals.data_high_current.connect(self._record_high_current_readings)
            data.signals.data_high_power_factor.connect(self._record_high_power_factor_readings)
            data.signals.data_high_real_power.connect(self._record_high_real_power_readings)

            data.signals.data_low_voltage.connect(self._record_low_voltage_readings)
            data.signals.data_low_current.connect(self._record_low_current_readings)
            data.signals.data_low_power_factor.connect(self._record_low_power_factor_readings)
            data.signals.data_low_real_power.connect(self._record_low_real_power_readings)

            data.signals.data_temperature.connect(self._record_temperature_readings)
            data.signals.data_scale_current.connect(self._record_scale_current_readings)
            data.signals.data_scale_voltage.connect(self._record_scale_voltage_readings)
            data.signals.data_correction_angle.connect(self._record_correction_angle_readings)

            data.signals.finished.connect(self._update_from_model)
            data.signals.resize_columns.connect(self._resize_table_columns)

            worker = ReadingsWorker(data)
            self.thread_pool.start(worker)

            if self.menu_helper.action_read_hi_or_low_voltage.data() == '7200':
                self.menu_helper.action_check_persistence.setEnabled(True)

            self.unsaved_test_results = True

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
                if index == 13 or index == 18:
                    self.qtw_sensors.cellWidget(line_position, index).setCurrentIndex(3)
                else:
                    self.qtw_sensors.item(line_position, index).setText("NA")

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

        spreadsheet.save_sensor_data(self.spreadsheet_path, data_sets)

        self.unsaved_test_results = False

    def _update_table_with_reading(self, location, content):
        if self.sensor_log.get_sensor_by_line_position(location[0]).linked:
            item: QTableWidgetItem = self.qtw_sensors.item(location[0], location[1])
            item.setText(content)

    def _update_from_model(self):
        for index, unit in enumerate(self.sensor_log):
            for j in range(1, 18):

                # handle fault current
                if unit.linked and j == 13:
                    fc = unit.fault_current
                    combo_index = 0
                    if fc == "Pass":
                        combo_index = 1
                    elif fc == "Fail":
                        combo_index = 2
                    self.qtw_sensors.cellWidget(index, j).setCurrentIndex(combo_index)

                # update table widget with current data if unit linked or j == rssi or firmware version index
                elif unit.linked or j == 2 or j == 3:
                    self.qtw_sensors.item(index, j).setText(unit.__getattribute__(_DATA_IN_TABLE_ORDER[j - 1]))

            # if unit.linked:
            #     self._set_field_background(index, 0, QBrush(QColor(0, 255, 0, 75)))

    def _create_toolbar(self):
        toolbar = QToolBar("ToolBar")
        self.addToolBar(toolbar)

        toolbar.addAction(self.menu_helper.action_configure)
        self.menu_helper.action_configure.setData(self._configure_collector_serial_numbers)
        self.menu_helper.action_configure.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_upgrade)
        self.menu_helper.action_upgrade.setData(lambda: self._upgrade_sensor_at_row_col(
            self.qtw_sensors.currentRow()))
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
            # self.browser = webdriver.Chrome(executable_path=self.settings.value("drivers/chromedriver"))
            self.browser = webdriver.Remote(service.service_url)
            # self.browser.minimize_window()
            # self.browser = chrome_worker.get_browser()

        return self.browser

    def _get_sensor_count(self):
        return len(self.sensor_log)

    def _set_field_background(self, row: int, col: int, color: QBrush):
        item: QTableWidgetItem = self.qtw_sensors.item(row,col)
        item.setBackground(color)
