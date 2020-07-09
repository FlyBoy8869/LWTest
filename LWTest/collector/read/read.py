from PyQt5.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from LWTest.constants import dom, LWTConstants as LWT
from LWTest.utilities import returns
from LWTest.utilities.misc import get_page_login_if_needed, normalize_reading, x_is_what_percent_of_y, filter_out_na


class Signals(QObject):
    data_fault_current = pyqtSignal(str)
    data_persisted = pyqtSignal(list)
    data_reading_persisted = pyqtSignal(str, int, int)

    data_reporting_data = pyqtSignal(int, str)
    data_reporting_data_complete = pyqtSignal()

    data_reading = pyqtSignal(tuple, str)
    data_readings_complete = pyqtSignal()

    high_data_readings = pyqtSignal(tuple)
    low_data_readings = pyqtSignal(tuple)
    page_load_error = pyqtSignal()

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

    def read(self, browser: webdriver.Chrome, count: int) -> returns.Result:
        browser.get(self._sensor_data_url)
        if "Auto Update" not in browser.page_source:
            self.signals.page_load_error.emit()
            return returns.Result(False, None, "Error.")
        readings = browser.find_elements_by_css_selector("div.tcellShort:not([id^='last'])")

        # voltage, current, power factor, real power
        results = self._extract_sensor_readings(readings, count)
        results[3] = self._massage_real_power_readings(results[3])
        temperature_readings = self._scrape_readings(readings, "textContent", len(readings) - count, len(readings))

        if self._reading_high_voltage(results[0]):
            self.signals.high_data_readings.emit(tuple(results))

        else:  # these readings gathered only when low voltage is dialed in
            get_page_login_if_needed(self._raw_configuration_url, browser)
            readings = browser.find_elements_by_css_selector("div.tcell > input")

            # scale current, scale voltage, correction angle
            advanced_readings = self._extract_advanced_readings(readings, count)

            results.extend(advanced_readings)
            results.append(temperature_readings)
            self.signals.low_data_readings.emit(
                tuple(results)
            )

            return returns.Result(True, None)

    def _extract_sensor_readings(self, readings, count):
        voltage_index = 0
        current_index = voltage_index + count
        power_factor_index = current_index + count
        lead_lag_index = power_factor_index + count
        real_power_index = lead_lag_index + count

        reading_slice_indexes = [
            [voltage_index, count],
            [current_index, current_index + count],
            [power_factor_index, power_factor_index + count],
            [real_power_index, real_power_index + count]
        ]

        return [self._scrape_readings(readings, "textContent", start, stop) for start, stop in reading_slice_indexes]

    def _extract_advanced_readings(self, readings, count):
        scale_current_index = 0
        scale_voltage_index = scale_current_index + count
        correction_angle_index = 12 if scale_voltage_index == 3 else 24

        reading_slice_indexes = [
            [scale_current_index, count],
            [scale_voltage_index, scale_voltage_index + count],
            [correction_angle_index, correction_angle_index + count]
        ]

        return [self._scrape_readings(readings, "value", start, stop) for start, stop in reading_slice_indexes]

    @staticmethod
    def _massage_real_power_readings(readings):
        return [str(int(float(normalize_reading(value)) * 1000))
                if value != LWT.NO_DATA else "NA"
                for value in readings]

    @staticmethod
    def _scrape_readings(readings, attribute: str, start: int, stop: int):
        return [value.get_attribute(attribute) for value in readings[start:stop]]

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
        """Return the number of readings that are considered high voltage. Readings should not contain 'N/A' values."""

        return len([reading for reading in readings
                    if
                    float(normalize_reading(reading)) > DataReader._HIGH_LOW_THRESHOLD
                    ])


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
        super().__init__()
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
            if content == LWT.NO_DATA:
                reporting_data = "Fail"

            self.signals.data_reporting_data.emit(self.line_position, reporting_data)
        except TimeoutException:
            pass

        self.signals.data_reporting_data_complete.emit()


class FirmwareVersionReader:
    """Used every time a sensor joins and links to the Collector."""

    def __init__(self, index, url: str, browser: webdriver.Chrome):
        super().__init__()
        self.url = url
        self.driver = browser
        self.index = index
        self.signals = Signals()

    def read(self):
        print(f"FirmwareVersionReader.run() called for index {self.index}")
        self.driver.get(self.url)

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, dom.firmware_version[self.index])))
            content = element.get_attribute("textContent")
            print(f"Firmware for index {self.index} = {content}")
            self.signals.firmware_version.emit((self.index, LWT.TableColumn.FIRMWARE), content)
        except TimeoutException:
            pass

        self.signals.firmware_check_complete.emit(self.index)
