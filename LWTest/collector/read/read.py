from time import sleep

from PyQt5.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from LWTest import LWTConstants as LWT
from LWTest.config.dom import constants as dom, constants
from LWTest.utilities.misc import get_page_login_if_needed


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
    data_readings_complete = pyqtSignal()

    resize_columns = pyqtSignal()

    firmware_version = pyqtSignal(tuple, str)
    firmware_check_complete = pyqtSignal(int)
    finished = pyqtSignal()


class DataReader:
    def __init__(self, url_1: str, url_2: str, browser: webdriver.Chrome, count: int, voltage_level: str,
                 validator, scale_and_angle_validator=None, temperature_validator=None):

        if voltage_level == "7200":
            assert scale_and_angle_validator is not None, ("You must provide a scale_n_angle_validator" +
                                                           " when the voltage_level is '7200'")
            assert temperature_validator is not None, ("You must provide a temperature_validator" +
                                                       " when the voltage_level is '7200'")

        self.url_sensor_data = url_1
        self.url_raw_configuration = url_2
        self.browser = browser
        self.count = count
        self.voltage_level = voltage_level
        self.validator = validator
        self.scale_and_angle_validator = scale_and_angle_validator
        self.temperature_validator = temperature_validator
        self.signals = Signals()

    def read(self):
        signal_voltage: pyqtSignal
        signal_current: pyqtSignal
        signal_power_factor: pyqtSignal
        signal_real_power: pyqtSignal

        self.browser.get(self.url_sensor_data)

        if self.voltage_level == "13800":
            signal_voltage = self.signals.data_high_voltage
            signal_current = self.signals.data_high_current
            signal_power_factor = self.signals.data_high_power_factor
            signal_real_power = self.signals.data_high_real_power
        else:
            signal_voltage = self.signals.data_low_voltage
            signal_current = self.signals.data_low_current
            signal_power_factor = self.signals.data_low_power_factor
            signal_real_power = self.signals.data_low_real_power

        try:
            voltage_readings = []
            for index, element in enumerate(dom.phase_voltage[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                voltage_readings.append(content)
            signal_voltage.emit(voltage_readings)

            current_readings = []
            for index, element in enumerate(dom.phase_current[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                current_readings.append(content)
            signal_current.emit(current_readings)

            factor_readings = []
            for index, element in enumerate(dom.phase_power_factor[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                factor_readings.append(content)
            signal_power_factor.emit(factor_readings)

            power_readings = []
            for index, element in enumerate(dom.phase_real_power[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("textContent")
                if content != 'NA':
                    content = str(int(float(content.replace(",", "")) * 1000))
                power_readings.append(content)
            signal_real_power.emit(power_readings)

            readings = tuple(zip(voltage_readings, current_readings, power_readings))
            self.validator(readings)

            if self.voltage_level == "7200":
                get_page_login_if_needed(self.url_raw_configuration, self.browser)

                scale_current_readings = []
                for index, element in enumerate(dom.scale_current[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    scale_current_readings.append(content)
                self.signals.data_scale_current.emit(scale_current_readings)

                scale_voltage_readings = []
                for index, element in enumerate(dom.scale_voltage[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    scale_voltage_readings.append(content)
                self.signals.data_scale_voltage.emit(scale_voltage_readings)

                correction_angle_readings = []
                for index, element in enumerate(dom.raw_configuration_angle[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("value")
                    correction_angle_readings.append(content)
                self.signals.data_correction_angle.emit(correction_angle_readings)

                readings = tuple(zip(scale_current_readings, scale_voltage_readings, correction_angle_readings))
                self.scale_and_angle_validator(readings)

                self.browser.get(LWT.URL_SENSOR_DATA)
                temperature_readings = []
                for index, element in enumerate(dom.phase_temperature[:self.count]):
                    field = self.browser.find_element_by_xpath(element)
                    content = field.get_attribute("textContent")
                    temperature_readings.append(content)
                self.signals.data_temperature.emit(temperature_readings)

                self.temperature_validator(temperature_readings)

        except StaleElementReferenceException:
            pass

        self.signals.finished.emit()
        self.signals.resize_columns.emit()


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

        element = dom.phase_voltage[self.line_position]
        field = self.browser.find_element_by_xpath(element)

        value = field.get_attribute("textContent")
        if value == "NA":
            reporting_data = "Fail"

        self.signals.data_reporting_data.emit(self.line_position, reporting_data)


class FirmwareVersionReader:
    """Used every time a sensor joins and links to the Collector."""

    def __init__(self, index, url: str, browser: webdriver.Chrome):
        self.url = url
        self.browser = browser
        self.index = index
        self.signals = Signals()

    def read(self):
        self.browser.get(self.url)

        field = self.browser.find_element_by_xpath(constants.firmware_version[self.index])
        content = field.get_attribute("textContent")

        self.signals.firmware_version.emit((self.index, LWT.TableColumn.FIRMWARE), content)
        self.signals.firmware_check_complete.emit(self.index)
