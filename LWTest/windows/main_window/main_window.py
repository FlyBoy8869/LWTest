import datetime

from PyQt5.QtCore import QThreadPool, QSettings, Qt, QItemSelectionModel
from PyQt5.QtGui import QIcon, QCloseEvent
from PyQt5.QtWidgets import QMainWindow, QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox, QToolBar
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from LWTest import sensor, signals
from LWTest.collector import configuration
from LWTest.collector.readings import Data, FaultCurrent, Persistence
from LWTest.config.app import logging as lwt_logging, settings as lwt_settings
from LWTest.config.dom import constants
from LWTest.spreadsheet import spreadsheet
from LWTest.utilities import utilities
from LWTest.windows.main_window.create_menus import MenuHelper
from LWTest.windows.main_window.menu_file_handlers import menu_file_save_handler
from LWTest.windows.main_window.menu_help_handlers import menu_help_about_handler
from LWTest.workers import upgrade_worker
from LWTest.workers.firmware_worker import FirmwareWorker
from LWTest.workers.link_worker import LinkWorker
from LWTest.workers.serial_config_worker import SerialConfigWorker

lwt_settings.load(r"LWTest/resources/config/config.txt")
lwt_logging.initialize()

service = Service(r"LWTest\resources\drivers\chromedriver\windows\version_78-0-3904-70\chromedriver.exe")
service.start()


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

        self.browser: webdriver.Chrome = self._get_browser()
        utilities.load_start_page(self.browser)
        # self.browser.maximize_window()

        self.activateWindow()

    def closeEvent(self, closing_event: QCloseEvent):
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
            result = QMessageBox.question(self, f"{dialog_title()} - Unsaved Test Results",
                                          "Discard results?\t\t\t\t",
                                          QMessageBox.Yes | QMessageBox.No,
                                          QMessageBox.No)

            if result == QMessageBox.No:
                return False

        if clear_flag:
            self.unsaved_test_results = False

        return True

    def _import_serial_numbers(self, filename: str):
        sn = spreadsheet.get_serial_numbers(filename)

        headers = ["Serial Number", "RSSI", "Firmware", "Data",
                   "13.8K", "120A", "Power Factor", "Real Power",
                   "7.2K", "60A", "Power Factor", "Real Power",
                   "Temperature", "Fault Current", "Scale Current", "Scale Voltage",
                   "Correction Angle", "Persists"]

        self.qtw_sensors.clear()
        rows_needed = len([s for s in sn if s != "0"])
        self.qtw_sensors.setRowCount(rows_needed)
        self.qtw_sensors.setColumnCount(len(headers))
        self.qtw_sensors.setHorizontalHeaderLabels(headers)

        for index, number in enumerate(sn):
            if number != "0":
                item = self._create_item(number)
                self.qtw_sensors.setItem(index, 0, item)

                for column in range(1, len(headers)):
                    item = self._create_item()
                    self.qtw_sensors.setItem(index, column, item)

        self.qtw_sensors.setCurrentCell(0, 0, QItemSelectionModel.NoUpdate)

        self.signals.adjust_size.emit()
        self.signals.serial_numbers_imported.emit(tuple(sn))

    def _resize_table(self):
        window_width = int(self.settings.value("geometry/mainwindow/width", "435"))
        window_height = int(self.settings.value("geometry/mainwindow/height", "244"))
        self.resize(window_width, window_height)

    def _configure_collector_serial_numbers(self, serial_numbers):
        config_worker = SerialConfigWorker(serial_numbers,
                                           self.settings.value("main/config_password"),
                                           self._get_browser(),
                                           self.settings.value("pages/configuration"))
        config_worker.signals.configured_serial_numbers.connect(self._determine_link_status)
        config_worker.signals.serial_config_page_failed_to_load.connect(self._serial_config_page_failed_to_load)

        self.thread_pool.start(config_worker)

    def _determine_link_status(self, serial_numbers):
        link_worker = LinkWorker(serial_numbers, self.settings.value("pages/modem_status"))
        link_worker.signals.url_read_exception.connect(self._link_error_handler)
        link_worker.signals.successful_link.connect(self._sensor_linked)
        link_worker.signals.link_timeout.connect(self._warn_sensors_not_linked)
        link_worker.signals.link_timeout.connect(self._read_current_firmware_version)
        link_worker.signals.link_activity.connect(self._link_show_activity)
        self.thread_pool.start(link_worker)

    def _link_error_handler(self, info):
        msg_box = QMessageBox(QMessageBox.Warning,
                              dialog_title(),
                              "Error while checking link status.\n\n" +
                              f"{info[1]}",
                              QMessageBox.Ok | QMessageBox.Retry, self)

        msg_box.setDetailedText(f"{info[2]}")

        button = msg_box.exec_()

        if button == QMessageBox.Retry:
            self._determine_link_status(self.sensor_log.get_serial_numbers())

    def _serial_config_page_failed_to_load(self, url: str, serial_numbers: tuple):
        button = QMessageBox.warning(self, "LWTest - Page Load Error", f"Failed to load {url}\n\n" +
                                     "Check the collector and click 'Ok' to retry.",
                                     QMessageBox.Ok | QMessageBox.Cancel)

        if button == QMessageBox.Ok:
            self._configure_collector_serial_numbers(serial_numbers)

    def _sensor_linked(self, data):
        items = self.qtw_sensors.findItems(data[0], Qt.MatchExactly)
        if items:
            row = self.qtw_sensors.row(items[0])
            new_item = self._create_item(data[1])
            self.qtw_sensors.setItem(row, 1, new_item)

    def _warn_sensors_not_linked(self, serial_numbers):
        # responds to link_worker.link_timeout
        for serial_number in serial_numbers:
            if serial_number != "0":
                self._update_rssi_column(serial_number, "Not Linked")

    def _link_show_activity(self, serial_numbers, indicator):
        for serial_number in serial_numbers:
            if serial_number != "0":
                self._update_rssi_column(serial_number, indicator)

    def _upgrade_firmware_handler(self, serial_number: str, row: int, ignore_failures=False):
        if not self.firmware_upgrade_in_progress:
            settings = QSettings()
            self.firmware_upgrade_in_progress = True

            # start sensor firmware upgrade
            browser = self._get_browser()
            browser.get(settings.value('pages/software_upgrade'))
            browser.find_element_by_xpath(constants.unit_select_button[row]).click()
            browser.find_element_by_xpath(constants.firmware_file).send_keys(
                "LWTest/resources/firmware/firmware-0x0075.zip")
            browser.find_element_by_xpath(constants.upgrade_password).send_keys(settings.value('main/config_password'))
            browser.find_element_by_xpath(constants.upgrade_button).click()
            #
            # sleep(1)
            #
            date = datetime.datetime.now()
            file = f"{date.year}-{date.month:02d}-{date.day:02d}_UPDATER.txt"
            # upgrade_log = f"http://192.168.2.1/index.php/log_viewer/view/{file}"
            upgrade_log = settings.value("pages/software_upgrade_log")

            worker = upgrade_worker.UpgradeWorker(serial_number, upgrade_log,
                                                  ignore_failures=ignore_failures)
            worker.signals.upgrade_successful.connect(self._upgrade_successful)
            worker.signals.upgrade_timed_out.connect(self._upgrade_timed_out)
            worker.signals.upgrade_show_activity.connect(self._upgrade_show_activity)
            worker.signals.upgrade_failed_to_enter_program_mode.connect(self._failed_to_enter_program_mode)
            self.thread_pool.start(worker)

    def _update_persistence_column(self, persist: str, row: int, col: int):
        self.qtw_sensors.item(row, col).setText(persist)

    def _upgrade_successful(self, serial_number):
        self._update_firmware_column(serial_number, "0x0075")
        self.firmware_upgrade_in_progress = False
        QMessageBox.information(QMessageBox(self), dialog_title(), "Sensor firmware successfully upgraded.",
                                QMessageBox.Ok)

    def _failed_to_enter_program_mode(self, serial_number):
        result = QMessageBox.warning(QMessageBox(self), dialog_title(), "Failed to enter program mode.",
                                     QMessageBox.Retry | QMessageBox.Cancel)

        self.firmware_upgrade_in_progress = False
        if result == QMessageBox.Retry:
            row = self.sensor_log.get_line_position_of_sensor(serial_number)
            self._upgrade_firmware_handler(serial_number, row, ignore_failures=True)

    def _upgrade_show_activity(self, serial_number):
        items = self.qtw_sensors.findItems(serial_number, Qt.MatchExactly)
        if items:
            row = self.qtw_sensors.row(items[0])
            item: QTableWidgetItem = self.qtw_sensors.item(row, 2)
            if len(item.text()) < 5:
                text = item.text() + "-"
                item.setText(text)
            else:
                item.setText("-")

    def _upgrade_timed_out(self, serial_number):
        self.firmware_upgrade_in_progress = False
        self._update_firmware_column(serial_number, "")

        QMessageBox.warning(QMessageBox(self), f"{dialog_title()} - Upgrading Sensor", "Process timed out.\t\t",
                            QMessageBox.Ok)

    def _check_persistence(self):
        settings = QSettings()

        if self.menu_helper.action_read_hi_or_low_voltage.data() == "7200":

            persistence = Persistence()
            persistence.signals.data_persisted.connect(self._update_persistence_column)
            persistence.check_persistence(settings.value("pages/raw_configuration"),
                                          self._get_browser(),
                                          self.qtw_sensors,
                                          self.sensor_log.get_actual_count())

    def _config_correction_angle(self):
        settings = QSettings()

        while True:
            count = len([sn for sn in self.sensor_log.get_serial_numbers() if sn != "0"])
            result = configuration.configure_correction_angle(settings.value('pages/configuration'),
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

    def _create_item(self, text=""):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        return item

    def _do_advanced_configuration(self):
        self._get_browser()
        count = len([sn for sn in self.sensor_log.get_serial_numbers() if sn != "0"])
        configuration.do_advanced_configuration(count, self._get_browser())

    def _find_item_row_col(self, text):
        items = self.qtw_sensors.findItems(text, Qt.MatchExactly)
        if items:
            row = self.qtw_sensors.row(items[0])
            col = self.qtw_sensors.column(items[0])
            item: QTableWidgetItem = self.qtw_sensors.item(row, col)

            return item, row, col

        return None

    def _read_current_firmware_version(self):
        settings = QSettings()
        count = self.sensor_log.get_actual_count()
        firmware_worker = FirmwareWorker(settings.value('pages/software_upgrade'), self._get_browser(), count)
        firmware_worker.signals.firmware_version.connect(self._update_firmware_version_column)
        self.thread_pool.start(firmware_worker)

    def _read_fault_current(self):
        settings = QSettings()

        fault_current = FaultCurrent(settings.value('pages/fault_current'), self._get_browser())
        fault_current.signals.fault_current.connect(self._update_fault_current_readings)
        fault_current.read_fault_current()

    def _take_readings(self):
        settings = QSettings()
        count = len([sn for sn in self.sensor_log.get_serial_numbers() if sn != "0"])
        data = Data(settings.value('pages/sensor_data'),
                    settings.value('pages/raw_configuration'),
                    self._get_browser(), count)
        data.signals.data_reading.connect(self._update_table_with_reading)
        data.read_data(self.menu_helper.action_read_hi_or_low_voltage.data())

    def _update_cell(self, serial_number, column, text):
        serial_item = self._find_item_row_col(serial_number)
        target_item: QTableWidgetItem = self.qtw_sensors.item(serial_item[1], column)

        target_item.setText(text)

    def _update_fault_current_readings(self, value):
        for index in range(self.sensor_log.get_actual_count()):
            item = self.qtw_sensors.item(index, 13)
            item.setText(value)

    def _update_firmware_column(self, serial_number, text):
        self._update_cell(serial_number, 2, text)

    def _update_firmware_version_column(self, location, version):
        item = self.qtw_sensors.item(location[0], location[1])
        item.setText(version)

    def _update_rssi_column(self, serial_number, text):
        self._update_cell(serial_number, 1, text)

    def _update_table_with_reading(self, location, content):
        # TODO: validate reading
        item: QTableWidgetItem = self.qtw_sensors.item(location[0], location[1])
        item.setText(content)

    def _create_toolbar(self):
        toolbar = QToolBar("ToolBar")
        self.addToolBar(toolbar)

        toolbar.addAction(self.menu_helper.action_configure)
        self.menu_helper.action_configure.setData(lambda: self._configure_collector_serial_numbers(
            self.sensor_log.get_serial_numbers()))
        self.menu_helper.action_configure.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_upgrade)
        self.menu_helper.action_upgrade.setData(lambda: self._upgrade_firmware_handler(
            self.qtw_sensors.item(self.qtw_sensors.currentRow(), 0).text(), self.qtw_sensors.currentRow()))
        self.menu_helper.action_upgrade.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_advanced_configuration)
        self.menu_helper.action_advanced_configuration.setData(self._do_advanced_configuration)
        self.menu_helper.action_advanced_configuration.triggered.connect(self._action_router)

        toolbar.addAction(self.menu_helper.action_calibrate)

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
        self.menu_helper.action_save.setData(menu_file_save_handler)
        self.menu_helper.action_save.triggered.connect(self._action_router)

        self.menu_helper.insert_spacer(toolbar, self)
        toolbar.addAction(self.menu_helper.action_exit)

    def _get_browser(self):
        if self.browser is None:
            # self.browser = webdriver.Chrome(executable_path=self.settings.value("drivers/chromedriver"))
            self.browser = webdriver.Remote(service.service_url)
            # self.browser = chrome_worker.get_browser()

        return self.browser

    def _close_browser(self):
        if self.browser:
            self.browser.quit()
            self.browser = None

    def _action_router(self):
        if self.sensor_log.is_empty():
            return

        if self.sender() is not None:
            self.sender().data()()
