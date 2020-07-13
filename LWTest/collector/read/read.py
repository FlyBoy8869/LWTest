from typing import List

from PyQt5.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import LWTest.utilities.misc as utils_misc
from LWTest.constants import lwt
from LWTest.utilities import returns


class Signals(QObject):
    data_fault_current = pyqtSignal(str)

    data_reading = pyqtSignal(tuple, str)
    data_readings_complete = pyqtSignal()

    high_data_readings = pyqtSignal(tuple)
    low_data_readings = pyqtSignal(tuple)
    page_load_error = pyqtSignal()

    resize_columns = pyqtSignal()

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
            utils_misc.get_page_login_if_needed(self._raw_configuration_url, browser)
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
        return [str(int(float(utils_misc.normalize_reading(value)) * 1000))
                if value != lwt.NO_DATA else "NA"
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
        filtered_readings = utils_misc.filter_out_na(readings)
        number_of_readings = len(filtered_readings)
        number_of_high_voltage_readings = DataReader._count_high_voltage_readings(filtered_readings)

        return utils_misc.x_is_what_percent_of_y(number_of_high_voltage_readings, number_of_readings)

    @staticmethod
    def _count_high_voltage_readings(readings) -> int:
        """Return the number of readings that are considered high voltage. Readings should not contain 'N/A' values."""

        return len([reading for reading in readings
                    if
                    float(utils_misc.normalize_reading(reading)) > DataReader._HIGH_LOW_THRESHOLD
                    ])


class PersistenceComparator:
    class Signals(QObject):
        persisted = pyqtSignal(list)
        finished = pyqtSignal()

    def __init__(self):
        self.signals = self.Signals()

    def compare(self, saved_readings, sensor_count: int, url: str, driver: webdriver.Chrome):
        self.signals.persisted.emit(
            self._compare(
                saved_readings,
                self._live_readings(sensor_count, url, driver)
            )
        )
        self.signals.finished.emit()

    def _live_readings(self, sensor_count: int, url: str, driver: webdriver.Chrome):
        return self._reading_element_values(
            self._reading_elements(url, driver),
            sensor_count
        )

    @staticmethod
    def _reading_elements(url: str, driver: webdriver.Chrome):
        utils_misc.get_page_login_if_needed(url, driver)
        return driver.find_elements_by_css_selector("div.tcell > input")

    def _reading_element_values(self, reading_elements, count: int):
        return tuple(
            zip(
                self._get_scale_current_values(reading_elements, count),
                self._get_scale_voltage_values(reading_elements, count),
                self._get_correction_angle_values(reading_elements, count)
            )
        )

    def _get_scale_current_values(self, elements, count: int):
        return self._get_values(elements, start=0, stop=count)

    def _get_scale_voltage_values(self, elements, count: int):
        return self._get_values(elements, start=count, stop=count * 2)

    def _get_correction_angle_values(self, elements, count: int):
        return self._get_values(elements, start=count * 4, stop=count * 4 + count)

    @staticmethod
    def _get_values(elements, *, start, stop):
        return [reading.get_attribute("value") for reading in elements[start:stop]]

    @staticmethod
    def _compare(saved_readings, live_readings) -> List[str]:
        persistence_results = ["Yes"] * len(saved_readings)

        for sensor_index, sensor_readings in enumerate(saved_readings):
            if live_readings[sensor_index] != sensor_readings:
                persistence_results[sensor_index] = "Failed"

        return persistence_results


class ReportingDataReader:
    class Signals(QObject):
        reporting = pyqtSignal(int, str)
        finished = pyqtSignal()

    def __init__(self):
        self.signals = self.Signals()

    def read(self, phase: int, url: str, driver: webdriver.Chrome):
        driver.get(url)

        try:
            elements = WebDriverWait(driver, 10).until(
                ec.presence_of_all_elements_located((By.CSS_SELECTOR, "div.tcellShort:not([id^='last'])")))

            reporting = "Fail" if elements[phase].get_attribute("textContent") == lwt.NO_DATA else "Pass"
        except TimeoutException:
            reporting = "Fail"

        self.signals.reporting.emit(phase, reporting)
        self.signals.finished.emit()


class FirmwareVersionReader:
    """Scrapes the sensors firmware version from the Software Upgrade page."""

    class Signals(QObject):
        version = pyqtSignal(int, str)
        finished = pyqtSignal()

    def __init__(self):
        self.signals = self.Signals()

    def read(self, phase: int, url: str, driver: webdriver.Chrome):
        driver.get(url)

        try:
            firmware_version_elements = WebDriverWait(driver, 10).until(
                ec.presence_of_all_elements_located((By.CSS_SELECTOR, "div.tcell")))[2:13:2]
            version = firmware_version_elements[phase].get_attribute("textContent")
        except TimeoutException:
            version = lwt.NO_DATA

        self.signals.version.emit(phase, version)
        self.signals.finished.emit()
