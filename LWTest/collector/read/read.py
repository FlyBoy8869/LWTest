import logging
from functools import partial
from typing import List, Union, Tuple

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import LWTest.utilities.misc as utils_misc
from LWTest.collector import ReadingType
from LWTest.constants import lwt

_READING_SELECTOR = "div.tcellShort:not([id^='last'])"
_ADVANCED_CONFIG_SELECTOR = "div.tcell > input"


def _confirm(message, box_type=QMessageBox.question, title="") -> int:
    return box_type(None, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


_confirm_high_range = partial(_confirm, "Unable to determine test voltage.\n\nIs test voltage set to 13800KV?")
_confirm_continue = partial(
    _confirm,
    "Continuing will overwrite any existing entries for test voltage 13800KV.\n\nAre you sure?",
    QMessageBox.warning
)


def _get_columns(driver):
    return 6 if "phase 4" in driver.page_source.lower() else 3


def _get_elements(selector, driver):
    return driver.find_elements_by_css_selector(selector)


class DataReader(QObject):
    page_load_error = pyqtSignal()
    readings = pyqtSignal(tuple, int)

    _HIGH_VOLTAGE_THRESHOLD = 10500.0
    _HIGH_CURRENT_THRESHOLD = 90.0
    _HIGH_REAL_POWER_THRESHOLD = 1_000_000.0
    _PERCENTAGE_HIGH_VOLTAGE_READINGS = 66.0

    _HIGH_RANGE = 1
    _UNDETERMINED_RANGE = 0
    _LOW_RANGE = -1

    def __init__(self, sensor_data_url: str, raw_config_url: str) -> None:
        super().__init__()
        self._sensor_data_url = sensor_data_url
        self._raw_configuration_url = raw_config_url
        self._columns = None

    def read(self, driver: webdriver.Chrome):
        driver.get(self._sensor_data_url)
        if "Auto Update" not in driver.page_source:
            self.page_load_error.emit()
            return

        self._columns = _get_columns(driver)
        readings = _get_elements(_READING_SELECTOR, driver)
        voltage, current, power_factor, real_power = self._get_sensor_readings(readings, self._columns)
        real_power = DataReader._replace_real_power_readings_with_massaged_readings(real_power)
        temperature = DataReader._get_temperature_readings(readings, self._columns)

        readings_list_lists = [voltage, current, power_factor, real_power]
        if (range_ := DataReader._resolve_undetermined_state(self._readings_range(readings_list_lists))) == "QUIT":
            return

        if range_ == self._HIGH_RANGE:
            self.readings.emit(tuple(voltage), ReadingType.HIGH_VOLTAGE)
            self.readings.emit(tuple(current), ReadingType.HIGH_CURRENT)
            self.readings.emit(tuple(power_factor), ReadingType.HIGH_POWER_FACTOR)
            self.readings.emit(tuple(real_power), ReadingType.HIGH_REAL_POWER)
        else:  # these readings gathered only when low voltage is dialed in
            driver.get(self._raw_configuration_url)

            readings = _get_elements(_ADVANCED_CONFIG_SELECTOR, driver)
            scale_current, scale_voltage, correction_angle = DataReader._get_advanced_readings(
                readings, self._columns
            )

            self.readings.emit(tuple(voltage), ReadingType.LOW_VOLTAGE)
            self.readings.emit(tuple(current), ReadingType.LOW_CURRENT)
            self.readings.emit(tuple(power_factor), ReadingType.LOW_POWER_FACTOR)
            self.readings.emit(tuple(real_power), ReadingType.LOW_REAL_POWER)
            self.readings.emit(tuple(scale_current), ReadingType.SCALE_CURRENT)
            self.readings.emit(tuple(scale_voltage), ReadingType.SCALE_VOLTAGE)
            self.readings.emit(tuple(correction_angle), ReadingType.CORRECTION_ANGLE)
            self.readings.emit(tuple(temperature), ReadingType.TEMPERATURE)

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

        values = [DataReader._scrape_readings(readings, "textContent", start, stop)
                  for start, stop in reading_slice_indexes]

        voltage_list = values[0]
        values[0] = [value.replace(",", "") for value in voltage_list]

        return values

    @staticmethod
    def _scrape_advanced_readings(readings, columns) -> List[List[str]]:
        scale_current_index = 0
        scale_voltage_index = scale_current_index + columns
        correction_angle_index = 12 if scale_voltage_index == 3 else 24

        reading_slice_indexes = [
            [scale_current_index, columns],
            [scale_voltage_index, scale_voltage_index + columns],
            [correction_angle_index, correction_angle_index + columns]
        ]

        return [DataReader._scrape_readings(readings, "value", start, stop)
                for start, stop in reading_slice_indexes]

    @staticmethod
    def _scrape_temperature_readings(readings, columns):
        return DataReader._scrape_readings(
            readings, "textContent", len(readings) - columns, len(readings)
        )

    @staticmethod
    def _get_advanced_readings(readings, columns: int):
        # scale current, scale voltage, correction angle
        advanced_readings = DataReader._scrape_advanced_readings(readings, columns)
        return advanced_readings

    @staticmethod
    def _get_sensor_readings(readings, columns):
        return DataReader._extract_sensor_readings(readings, columns)

    @staticmethod
    def _get_temperature_readings(readings, columns):
        return DataReader._scrape_temperature_readings(readings, columns)

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

        def _filter_out_na(readings_: list) -> list:
            return list(filter(lambda r: r != lwt.NO_DATA, readings_))

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
    def _replace_real_power_readings_with_massaged_readings(power_readings):
        return DataReader._massage_real_power_readings(power_readings)

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
    persisted = pyqtSignal(tuple, int)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def compare(self, saved_readings, url: str, driver: webdriver.Chrome):
        driver.get(url)
        columns = _get_columns(driver)
        self.persisted.emit(
            self._compare(
                saved_readings,
                self._live_readings(columns, driver)
            ),
            ReadingType.PERSISTS
        )
        self.finished.emit()

    def _live_readings(self, sensor_count: int, driver: webdriver.Chrome):
        return self._reading_element_values(
            _get_elements(_ADVANCED_CONFIG_SELECTOR, driver),
            sensor_count
        )

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
    def _compare(saved_readings, live_readings) -> Tuple[str]:
        persistence_results = ["Pass"] * len(saved_readings)

        for sensor_index, sensor_readings in enumerate(saved_readings):
            if live_readings[sensor_index] != sensor_readings:
                persistence_results[sensor_index] = "Fail"

        return tuple(persistence_results)


class Reader(QObject):
    update = pyqtSignal(int, str)
    finished = pyqtSignal()

    ATTRIBUTE = "textContent"
    SELECTOR = ""
    RANGE_ = None
    URL = ""
    WAIT_TIME = 10

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)

    def read(self, phase: int, driver: webdriver.Chrome):
        return self._get_data(phase, driver)

    def _emit_signals(self, phase, data):
        self.update.emit(phase, data)
        self.finished.emit()

    def _get_data(self, phase: int, driver: webdriver.Chrome):
        try:
            elements = self._get_elements(self.SELECTOR, self.RANGE_, driver)
            content = elements[phase].get_attribute(self.ATTRIBUTE)
            return content
        except TimeoutException:
            return lwt.NO_DATA

    def _get_elements(self, selector: str, range_: slice, driver: webdriver.Chrome):
        driver.get(self.URL)
        elements = WebDriverWait(driver, self.WAIT_TIME).until(
            ec.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
        return elements[range_]


class ReportingDataReader(Reader):
    SELECTOR = "div.tcellShort:not([id^='last'])"
    RANGE_ = slice(-1)
    URL = lwt.URL_SENSOR_DATA

    def read(self, phase: int, driver: webdriver.Chrome):
        self._logger.debug(f"confirming Phase {phase + 1} is reading data")
        content = super().read(phase, driver)
        reporting = "Fail" if content == lwt.NO_DATA else "Pass"
        super()._emit_signals(phase, reporting)


class FirmwareVersionReader(Reader):
    """Scrapes the sensor's firmware version from the Software Upgrade page."""

    SELECTOR = "div.tcell"
    RANGE_ = slice(2, 13, 2)
    URL = lwt.URL_SOFTWARE_UPGRADE

    def read(self, phase: int, driver: webdriver.Chrome):
        self._logger.debug(f"reading firmware version for Phase {phase + 1}")
        version = super().read(phase, driver)
        super()._emit_signals(phase, version)
