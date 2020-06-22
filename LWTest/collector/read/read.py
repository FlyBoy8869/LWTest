from time import sleep

from PyQt5.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from LWTest import LWTConstants as LWT
from LWTest.constants import dom
from LWTest.utilities.misc import get_page_login_if_needed, normalize_reading, x_is_what_percent_of_y, filter_out_na


class Signals(QObject):
    data_fault_current = pyqtSignal(str)
    data_persisted = pyqtSignal(list)
    data_reading_persisted = pyqtSignal(str, int, int)
    data_reporting_data = pyqtSignal(int, str)
    data_reading = pyqtSignal(tuple, str)
    data_readings_complete = pyqtSignal()

    high_data_readings = pyqtSignal(tuple)
    low_data_readings = pyqtSignal(tuple)

    resize_columns = pyqtSignal()

    firmware_version = pyqtSignal(tuple, str)
    firmware_check_complete = pyqtSignal(int)
    finished = pyqtSignal()


class DataReader:
    _HIGH_LOW_THRESHOLD = 10500
    _PERCENTAGE_HIGH_VOLTAGE_READINGS = 66.0

    def __init__(self, sensor_data_url: str, raw_config_url: str) -> None:
        self._sensor_data_url = sensor_data_url
        self._raw_configuration_url = raw_config_url
        self.signals = Signals()

    def read(self, browser: webdriver.Chrome, count: int) -> None:
        browser.get(self._sensor_data_url)

        try:  # readings gathered regardless of whether high or low voltage is dialed in
            voltage_readings = []
            for index, element in enumerate(dom.phase_voltage[:count]):
                field = browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                voltage_readings.append(content)

            current_readings = []
            for index, element in enumerate(dom.phase_current[:count]):
                field = browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                current_readings.append(content)

            factor_readings = []
            for index, element in enumerate(dom.phase_power_factor[:count]):
                field = browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                factor_readings.append(content)

            power_readings = []
            for index, element in enumerate(dom.phase_real_power[:count]):
                field = browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                if content != LWT.NO_DATA:
                    content = str(int(float(normalize_reading(content)) * 1000))
                power_readings.append(content)

            if self._reading_high_voltage(voltage_readings):
                self.signals.high_data_readings.emit((voltage_readings,
                                                     current_readings,
                                                     factor_readings,
                                                     power_readings))

                return

            else:  # readings gathered only when low voltage is dialed in
                temperature_readings = []
                for index, element in enumerate(dom.phase_temperature[:count]):
                    field = browser.find_element_by_xpath(element)
                    content = field.get_attribute("textContent")
                    temperature_readings.append(content)

                get_page_login_if_needed(self._raw_configuration_url, browser)

                scale_current_readings = []
                for index, element in enumerate(dom.scale_current[:count]):
                    field = browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    scale_current_readings.append(content)

                scale_voltage_readings = []
                for index, element in enumerate(dom.scale_voltage[:count]):
                    field = browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    scale_voltage_readings.append(content)

                correction_angle_readings = []
                for index, element in enumerate(dom.raw_configuration_angle[:count]):
                    field = browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    correction_angle_readings.append(content)

                self.signals.low_data_readings.emit((voltage_readings,
                                                    current_readings,
                                                    factor_readings,
                                                    power_readings,
                                                    scale_current_readings,
                                                    scale_voltage_readings,
                                                    correction_angle_readings,
                                                    temperature_readings))

        except StaleElementReferenceException:
            pass

    @staticmethod
    def _reading_high_voltage(readings: list) -> bool:
        return True if DataReader._get_percentage_of_high_voltage_readings(readings)\
                       >= DataReader._PERCENTAGE_HIGH_VOLTAGE_READINGS else False

    @staticmethod
    def _get_percentage_of_high_voltage_readings(readings: list) -> float:
        filtered_readings = filter_out_na(readings)
        number_of_readings = len(filtered_readings)
        number_of_high_voltage_readings = DataReader._count_high_voltage_readings(filtered_readings)

        return x_is_what_percent_of_y(number_of_high_voltage_readings, number_of_readings)

    @staticmethod
    def _count_high_voltage_readings(readings) -> int:
        """Return the number of readings that are considered high voltage. Readings should not contain 'NA' values."""

        return len([reading for reading in readings
                    if float(normalize_reading(reading)) > DataReader._HIGH_LOW_THRESHOLD])


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

        self.signals.finished.emit()
        self.signals.resize_columns.emit()


class PersistenceReader:
    def __init__(self, url: str, browser: webdriver.Chrome, values: list):
        self.signals = Signals()
        self.url = url
        self.browser = browser
        self.values = values
        self.count = len(values)

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

        collector_readings = tuple(zip(scale_currents, scale_voltages, correction_angles))

        for sensor_index, sensor_readings in enumerate(self.values):
            if collector_readings[sensor_index] != sensor_readings:
                presumed_innocent[sensor_index] = "Failed"

        self.signals.data_persisted.emit(presumed_innocent)
        self.signals.finished.emit()
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

        try:
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, dom.phase_voltage[self.line_position])))

            content = element.get_attribute("textContent")
            if content == 'NA':
                reporting_data = "Fail"

            self.signals.data_reporting_data.emit(self.line_position, reporting_data)
        except TimeoutException:
            pass


class FirmwareVersionReader:
    """Used every time a sensor joins and links to the Collector."""

    def __init__(self, index, url: str, browser: webdriver.Chrome):
        self.url = url
        self.driver = browser
        self.index = index
        self.signals = Signals()

    def read(self):
        self.driver.get(self.url)

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, dom.firmware_version[self.index])))
            content = element.get_attribute("textContent")
            self.signals.firmware_version.emit((self.index, LWT.TableColumn.FIRMWARE), content)
        except TimeoutException:
            pass

        self.signals.firmware_check_complete.emit(self.index)
