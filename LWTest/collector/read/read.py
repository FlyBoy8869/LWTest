import logging
from functools import partial
from time import sleep
from typing import List, Union

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import LWTest.utilities.misc as utils_misc
from LWTest.constants import lwt

_READING_ELEMENTS = "div.tcellShort:not([id^='last'])"


def _confirm(message, box_type=QMessageBox.question, title="") -> int:
    return box_type(None, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


_confirm_high_range = partial(_confirm, "Unable to determine test voltage.\n\nIs test voltage set to 13800KV?")
_confirm_continue = partial(
    _confirm,
    "Continuing will overwrite any existing entries for test voltage 13800KV.\n\nAre you sure?",
    QMessageBox.warning
)


def _filter_out_na(readings: list) -> list:
    return list(filter(lambda r: r != lwt.NO_DATA, readings))


def _find_all_indexes_of_na_in_list(readings):
    indexes = []
    for index, value in enumerate(readings):
        if value == "NA":
            indexes.append(index)
    return indexes


def _get_columns(driver):
    return 6 if "phase 4" in driver.page_source.lower() else 3


def _get_elements(selector, driver):
    return driver.find_elements_by_css_selector(selector)


class DataReader:
    class Signals(QObject):
        high_data_readings = pyqtSignal(tuple)
        low_data_readings = pyqtSignal(tuple)
        page_load_error = pyqtSignal()

    _HIGH_VOLTAGE_THRESHOLD = 10500.0
    _HIGH_CURRENT_THRESHOLD = 90.0
    _HIGH_REAL_POWER_THRESHOLD = 1_000_000.0
    _PERCENTAGE_HIGH_VOLTAGE_READINGS = 66.0

    _HIGH_RANGE = 1
    _UNDETERMINED_RANGE = 0
    _LOW_RANGE = -1

    def __init__(self, sensor_data_url: str, raw_config_url: str) -> None:
        self.signals = self.Signals()
        self._sensor_data_url = sensor_data_url
        self._raw_configuration_url = raw_config_url
        self._columns = None

    def read(self, driver: webdriver.Chrome):
        driver.get(self._sensor_data_url)
        if "Auto Update" not in driver.page_source:
            self.signals.page_load_error.emit()

        self._columns = _get_columns(driver)
        readings = _get_elements(_READING_ELEMENTS, driver)
        # [voltage], [current], [power factor], [real power]
        results: List[List[str, ...]] = self._get_sensor_readings(readings, self._columns)
        DataReader._replace_real_power_readings_with_massaged_readings(results, 3)
        temperature_readings = DataReader._get_temperature_readings(readings, self._columns)

        if (range_ := DataReader._resolve_undetermined_state(self._readings_range(results))) == "QUIT":
            return

        if range_ == self._HIGH_RANGE:
            self.signals.high_data_readings.emit(tuple(results))
        else:  # these readings gathered only when low voltage is dialed in
            driver.get(self._raw_configuration_url)
            readings = _get_elements("div.tcell > input", driver)
            results = DataReader._get_advanced_readings(
                results,
                readings,
                self._columns
            )
            results.append(temperature_readings)
            self.signals.low_data_readings.emit(tuple(results))

    @staticmethod
    def _extract_sensor_readings(readings, columns):
        voltage_index = 0
        current_index = voltage_index + columns
        power_factor_index = current_index + columns
        lead_lag_index = power_factor_index + columns
        real_power_index = lead_lag_index + columns

        reading_slice_indexes = [
            [voltage_index, columns],
            [current_index, current_index + columns],
            [power_factor_index, power_factor_index + columns],
            [real_power_index, real_power_index + columns]
        ]

        return [DataReader._scrape_readings(readings, "textContent", start, stop)
                for start, stop in reading_slice_indexes]

    @staticmethod
    def _extract_advanced_readings(readings, columns) -> List[List[str]]:
        scale_current_index = 0
        scale_voltage_index = scale_current_index + columns
        correction_angle_index = 12 if scale_voltage_index == 3 else 24

        reading_slice_indexes = [
            [scale_current_index, columns],
            [scale_voltage_index, scale_voltage_index + columns],
            [correction_angle_index, correction_angle_index + columns]
        ]

        return [DataReader._scrape_readings(readings, "value", start, stop) for start, stop in reading_slice_indexes]

    @staticmethod
    def _extract_temperature_readings(readings, columns):
        return DataReader._scrape_readings(
            readings, "textContent", len(readings) - columns, len(readings)
        )

    @staticmethod
    def _get_advanced_readings(results: List[List[str]], readings, columns: int):
        # scale current, scale voltage, correction angle
        advanced_readings = DataReader._extract_advanced_readings(readings, columns)

        na_indexes: List[int, ...] = _find_all_indexes_of_na_in_list(results[0])
        for readings in advanced_readings:
            for index in na_indexes:
                readings[index] = lwt.NO_DATA

        results.extend(advanced_readings)
        return results

    @staticmethod
    def _get_sensor_readings(readings, columns):
        return DataReader._extract_sensor_readings(readings, columns)

    @staticmethod
    def _get_temperature_readings(readings, columns):
        return DataReader._extract_temperature_readings(readings, columns)

    @staticmethod
    def _massage_real_power_readings(readings) -> List[str]:
        return [str(int(float(utils_misc.normalize_reading(value)) * 1000))
                if value != lwt.NO_DATA else "NA"
                for value in readings]

    @staticmethod
    def _readings_range(readings: List[list]) -> int:
        """Returns:
            -1: low voltage
             0: indeterminate
             1: high voltage"""

        def _is_high_range_reading(reading_, threshold_) -> bool:
            return float(reading_) >= threshold_

        number_of_high_range_readings = 0
        voltage, current, power_factor, real_power = [_filter_out_na(reading_set) for reading_set in readings]
        real_power = DataReader._massage_real_power_readings(real_power)

        for readings, threshold in [
            (voltage, DataReader._HIGH_VOLTAGE_THRESHOLD),
            (current, DataReader._HIGH_CURRENT_THRESHOLD),
            (real_power, DataReader._HIGH_REAL_POWER_THRESHOLD)
        ]:
            for reading in readings:
                number_of_high_range_readings += _is_high_range_reading(reading, threshold)

        total_readings = len(voltage) + len(current) + len(real_power)
        percentage = number_of_high_range_readings / total_readings * 100
        if percentage == 50.0:
            return DataReader._UNDETERMINED_RANGE
        elif percentage > 50.0:
            return DataReader._HIGH_RANGE

        return DataReader._LOW_RANGE

    @staticmethod
    def _replace_real_power_readings_with_massaged_readings(results, index: int):
        results[index] = DataReader._massage_real_power_readings(results[index])

    @staticmethod
    def _resolve_undetermined_state(range_) -> Union[str, int]:
        if range_ == DataReader._UNDETERMINED_RANGE:
            if _confirm_high_range() == QMessageBox.Yes:
                if _confirm_continue() == QMessageBox.No:
                    return "QUIT"
                return DataReader._HIGH_RANGE
            else:
                return DataReader._LOW_RANGE

        return range_

    @staticmethod
    def _scrape_readings(readings, attribute: str, start: int, stop: int) -> List[str]:
        return [value.get_attribute(attribute) for value in readings[start:stop]]


class PersistenceComparator(QObject):
    persisted = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def compare(self, saved_readings, sensor_count: int, url: str, driver: webdriver.Chrome):
        self.persisted.emit(
            self._compare(
                saved_readings,
                self._live_readings(sensor_count, url, driver)
            )
        )
        self.finished.emit()

    def _live_readings(self, sensor_count: int, url: str, driver: webdriver.Chrome):
        return self._reading_element_values(
            self._read_elements(url, driver),
            sensor_count
        )

    @staticmethod
    def _read_elements(url: str, driver: webdriver.Chrome):
        driver.get(url)
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
        persistence_results = ["Pass"] * len(saved_readings)

        for sensor_index, sensor_readings in enumerate(saved_readings):
            if live_readings[sensor_index] != sensor_readings:
                persistence_results[sensor_index] = "Fail"

        return persistence_results


class Reader(QObject):
    update = pyqtSignal(int, str)
    finished = pyqtSignal()

    ATTRIBUTE = "textContent"
    SELECTOR = ""
    RANGE_ = None
    WAIT_TIME = 10

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)

    def read(self, phase: int, url: str, driver: webdriver.Chrome):
        return self._get_data(phase, url, driver)

    def _emit_signals(self, phase, data):
        self.update.emit(phase, data)
        self.finished.emit()

    def _get_data(self, phase: int, url: str, driver: webdriver.Chrome):
        driver.get(url)
        try:
            elements = self._get_elements(self.SELECTOR, self.RANGE_, driver)
            content = elements[phase].get_attribute(self.ATTRIBUTE)
            return content
        except TimeoutException:
            return ""

    def _get_elements(self, selector: str, range_: slice, driver: webdriver.Chrome):
        elements = WebDriverWait(driver, self.WAIT_TIME).until(
            ec.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
        return elements[range_]


class ReportingDataReader(Reader):
    SELECTOR = "div.tcellShort:not([id^='last'])"
    RANGE_ = slice(-1)

    def read(self, phase: int, url: str, driver: webdriver.Chrome):
        self._logger.debug(f"confirming Phase {phase + 1} is reading data")

        if not (content := super().read(phase, url, driver)):
            reporting = "Fail"
        else:
            reporting = "Fail" if content == lwt.NO_DATA else "Pass"

        super()._emit_signals(phase, reporting)


class FirmwareVersionReader(Reader):
    """Scrapes the sensor's firmware version from the Software Upgrade page."""

    SELECTOR = "div.tcell"
    RANGE_ = slice(2, 13, 2)

    def read(self, phase: int, url: str, driver: webdriver.Chrome):
        self._logger.debug(f"reading firmware version for Phase {phase + 1}")

        if not (version := super().read(phase, url, driver)):
            version = lwt.NO_DATA

        super()._emit_signals(phase, version)
