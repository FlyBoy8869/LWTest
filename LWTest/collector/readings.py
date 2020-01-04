from time import sleep

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QTableWidget
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from LWTest.config.dom import constants as dom, constants
from LWTest.utilities.misc import get_page_login_if_needed


# sensor table columns where data is to be recorded
high_data = (4, 5, 6, 7)
low_data = (8, 9, 10, 11)
temp = 12
fault_current = 13
software_version_col = 2
scale_current = 14
scale_voltage = 15
correction_angle = 16


class Signals(QObject):
    data_high_voltage = pyqtSignal(list)
    data_high_current = pyqtSignal(list)
    data_high_power_factor = pyqtSignal(list)
    data_high_real_power = pyqtSignal(list)
    data_temperature = pyqtSignal(list)
    data_low_voltage = pyqtSignal(list)
    data_low_current = pyqtSignal(list)
    data_low_power_factor = pyqtSignal(list)
    data_low_real_power = pyqtSignal(list)
    data_scale_current = pyqtSignal(list)
    data_scale_voltage = pyqtSignal(list)
    data_correction_angle = pyqtSignal(list)
    data_fault_current = pyqtSignal(str)
    data_persisted = pyqtSignal(list)
    data_reading_persisted = pyqtSignal(str, int, int)
    data_reporting_data = pyqtSignal(int, str)

    data_reading = pyqtSignal(tuple, str)

    resize_columns = pyqtSignal()

    firmware_version = pyqtSignal(tuple, str)
    firmware_check_complete = pyqtSignal(int)


class DataReader:
    def __init__(self, url_1: str, url_2: str, browser: webdriver.Chrome, count: int, voltage_level):
        self.url_1 = url_1
        self.url_2 = url_2
        self.browser = browser
        self.count = count
        self.voltage_level = voltage_level
        self.signals = Signals()

    def read(self):
        signal_voltage: pyqtSignal
        signal_current: pyqtSignal
        signal_power_factor: pyqtSignal
        signal_real_power: pyqtSignal

        self.browser.get(self.url_1)

        if self.voltage_level == "13800":
            data = high_data
            signal_voltage = self.signals.data_high_voltage
            signal_current = self.signals.data_high_current
            signal_power_factor = self.signals.data_high_power_factor
            signal_real_power = self.signals.data_high_real_power
        else:
            data = low_data
            signal_voltage = self.signals.data_low_voltage
            signal_current = self.signals.data_low_current
            signal_power_factor = self.signals.data_low_power_factor
            signal_real_power = self.signals.data_low_real_power

        try:
            readings = []
            for index, element in enumerate(dom.phase_voltage[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                readings.append(content)
                self.signals.data_reading.emit((index, data[0]), content)
            signal_voltage.emit(readings)

            readings.clear()
            for index, element in enumerate(dom.phase_current[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                readings.append(content)
                self.signals.data_reading.emit((index, data[1]), content)
            signal_current.emit(readings)

            readings.clear()
            for index, element in enumerate(dom.phase_power_factor[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                readings.append(content)
                self.signals.data_reading.emit((index, data[2]), content)
            signal_power_factor.emit(readings)

            readings.clear()
            for index, element in enumerate(dom.phase_real_power[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                if content != 'NA':
                    content = str(int(float(content.replace(",", "")) * 1000))
                readings.append(content)
                self.signals.data_reading.emit((index, data[3]), content)
            signal_real_power.emit(readings)

            readings.clear()
            for index, element in enumerate(dom.phase_temperature[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                readings.append(content)
                self.signals.data_reading.emit((index, temp), content)
            self.signals.data_temperature.emit(readings)

            if self.voltage_level == "7200":
                get_page_login_if_needed(self.url_2, self.browser)

                readings.clear()
                for index, element in enumerate(dom.scale_current[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    readings.append(content)
                    self.signals.data_reading.emit((index, scale_current), content)
                self.signals.data_scale_current.emit(readings)

                readings.clear()
                for index, element in enumerate(dom.scale_voltage[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    readings.append(content)
                    self.signals.data_reading.emit((index, scale_voltage), content)
                self.signals.data_scale_voltage.emit(readings)

                readings.clear()
                for index, element in enumerate(dom.raw_configuration_angle[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    readings.append(content)
                    self.signals.data_reading.emit((index, correction_angle), content)
                self.signals.data_correction_angle.emit(readings)

            self.signals.resize_columns.emit()
        except StaleElementReferenceException:
            pass


class FaultCurrentReader:
    def __init__(self, url: str, browser: webdriver.Chrome):
        self.url = url
        self.browser = browser
        self.signals = Signals()

    def read(self):
        self.browser.get(self.url)
        sleep(1)
        field = self.browser.find_element_by_xpath(dom.fault_current_1)
        if float(field.get_attribute("textContent")) >= 0.0:
            self.signals.data_fault_current.emit("Pass")
        else:
            self.signals.data_fault_current.emit("Fail")

        self.signals.resize_columns.emit()


class PersistenceReader:
    def __init__(self, url: str, browser: webdriver.Chrome, table: QTableWidget, count: int):
        self.signals = Signals()
        self.url = url
        self.browser = browser
        self.table = table
        self.count = count

    def read(self):
        get_page_login_if_needed(self.url, self.browser)

        # start with the assumption that values do persist
        presumed_innocent = ["Yes"] * self.count

        scale_currents = []
        scale_voltages = []
        correction_angles = []

        for element in dom.scale_current[:self.count]:
            field = self.browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            scale_currents.append(value)

        for element in dom.scale_voltage[:self.count]:
            field = self.browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            scale_voltages.append(value)

        for element in dom.raw_configuration_angle[:self.count]:
            field = self.browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            correction_angles.append(value)

        # then for each category, update that assumption if proven wrong

        for index in range(self.count):
            if scale_currents[index] != self.table.item(index, 14).text():
                presumed_innocent[index] = "Failed"

        for index in range(self.count):
            if scale_voltages[index] != self.table.item(index, 15).text():
                presumed_innocent[index] = "Failed"

        for index in range(self.count):
            if correction_angles[index] != self.table.item(index, 16).text():
                presumed_innocent[index] = "Failed"

        self.signals.data_persisted.emit(presumed_innocent)

        self.signals.resize_columns.emit()


class ReportingDataReader:
    def __init__(self, line_position, url: str, browser: webdriver.Chrome):
        self.line_position = line_position
        self.url = url
        self.browser = browser
        self.signals = Signals()

    def read(self):
        reporting_data = "Pass"

        self.browser.get(self.url)

        element = dom.phase_voltage[self.line_position]
        field = self.browser.find_element_by_xpath(element)

        value = field.get_attribute("textContent")
        if value == "NA":
            reporting_data = "Fail"

        self.signals.data_reporting_data.emit(self.line_position, reporting_data)


class FirmwareVersionReader:
    """Used every time a sensor joins and links to the Collector."""
    _firmware_version_col = 2

    def __init__(self, url: str, browser: webdriver.Chrome, index):
        self.url = url
        self.browser = browser
        self.index = index
        self.signals = Signals()

    def read(self):
        self.browser.get(self.url)

        field = self.browser.find_element_by_xpath(constants.firmware_version[self.index])
        content = field.get_attribute("textContent")

        self.signals.firmware_version.emit((self.index, self._firmware_version_col), content)
        self.signals.firmware_check_complete.emit(self.index)
