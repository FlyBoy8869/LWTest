from functools import partial
from typing import Union, List

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from selenium import webdriver

import LWTest.utilities.misc as utils_misc
import LWTest.constants.lwt_constants as lwt
from LWTest.collector.common.constants import ADVANCED_CONFIG_SELECTOR, READING_SELECTOR, ReadingType
from LWTest.collector.common import helpers


def _confirm(message, box_type=QMessageBox.question, title="") -> int:
    return box_type(None, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


_confirm_high_range = partial(_confirm, "Unable to determine test voltage.\n\nIs test voltage set to 13800KV?")
_confirm_continue = partial(
    _confirm,
    "Continuing will overwrite any existing entries for test voltage 13800KV.\n\nAre you sure?",
    QMessageBox.warning
)


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

        self._columns = helpers.get_columns(driver)
        readings = helpers.get_elements(READING_SELECTOR, driver)
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

            readings = helpers.get_elements(ADVANCED_CONFIG_SELECTOR, driver)
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
