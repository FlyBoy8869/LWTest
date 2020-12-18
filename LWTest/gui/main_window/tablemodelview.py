import logging
from collections import namedtuple

from PyQt5.QtCore import QMutex, QMutexLocker, QReadWriteLock
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from typing import Tuple, Callable, Union

import LWTest.gui.brushes as brushes
from LWTest.constants import lwt_constants as lwt
from LWTest.constants.lwt_constants.tolerance import Tolerance as tol
from LWTest.constants.lwt_constants.sensor_table_columns import TableColumn as tc
from LWTest.sensor import Sensor

_DATA_IN_TABLE_ORDER = ("rssi", "firmware_version", "reporting_data", "calibrated", "high_voltage", "high_current",
                        "high_power_factor", "high_real_power", "low_voltage", "low_current",
                        "low_power_factor", "low_real_power", "scale_current", "scale_voltage",
                        "correction_angle", "persists", "temperature", "fault_current")

WordMatch = namedtuple("WordMatch", "word")
ReadingLimits = namedtuple("ReadingLimits", "lower upper")


class Validator:
    @staticmethod
    def validate(reading, limits: Tuple[Union[float, str]]) -> bool:
        raise NotImplementedError("validate must be overridden")

    @staticmethod
    def get_brush(result: str):
        markers = {
            "IN": brushes.BRUSH_GOOD_READING,
            "OUT": brushes.BRUSH_BAD_READING,
            "NA": brushes.BRUSH_TRANSPARENT}
        return markers[result]

    @staticmethod
    def is_na(reading):
        return True if reading == "NA" else False


class WordMatchValidator(Validator):
    @staticmethod
    def validate(reading, limits: WordMatch) -> str:
        if WordMatchValidator.is_na(reading):
            return "NA"
        elif reading == limits.word:
            return "IN"
        else:
            return "OUT"


class FloatValidator(Validator):
    @staticmethod
    def validate(reading, limits: Tuple[float, ...]) -> str:
        lower, upper = limits
        if FloatValidator.is_na(reading):
            return reading

        return "IN" if lower < float(reading.replace(",", "")) < upper else "OUT"


validators_by_column = {
    tc.RSSI.value: (FloatValidator, (-75.0, 0)),
    tc.FIRMWARE.value: (WordMatchValidator, WordMatch('0x75',)),
    tc.REPORTING.value: (WordMatchValidator, WordMatch("Pass",)),
    tc.CALIBRATION: (None, None, None),
    tc.HIGH_VOLTAGE.value: (FloatValidator, ReadingLimits(tol.HIGH_VOLTAGE_MIN.value, tol.HIGH_VOLTAGE_MAX.value)),
    tc.HIGH_CURRENT.value: (FloatValidator, ReadingLimits(tol.HIGH_CURRENT_MIN.value, tol.HIGH_CURRENT_MAX.value)),
    tc.HIGH_POWER_FACTOR.value: (FloatValidator, ReadingLimits(0.8000, 1.0000)),
    tc.HIGH_REAL_POWER.value: (FloatValidator, ReadingLimits(tol.HIGH_POWER_MIN.value, tol.HIGH_POWER_MAX.value)),
    tc.LOW_VOLTAGE.value: (FloatValidator, ReadingLimits(tol.LOW_VOLTAGE_MIN.value, tol.LOW_VOLTAGE_MAX.value)),
    tc.LOW_CURRENT.value: (FloatValidator, ReadingLimits(tol.LOW_CURRENT_MIN.value, tol.LOW_CURRENT_MAX.value)),
    tc.LOW_POWER_FACTOR.value: (FloatValidator, ReadingLimits(0.8000, 1.0000)),
    tc.LOW_REAL_POWER.value: (FloatValidator, ReadingLimits(tol.LOW_POWER_MIN.value, tol.LOW_POWER_MAX.value)),
    tc.SCALE_CURRENT.value: (FloatValidator, ReadingLimits(tol.SCALE_CURRENT_MIN.value, tol.SCALE_CURRENT_MAX.value)),
    tc.SCALE_VOLTAGE.value: (FloatValidator, ReadingLimits(tol.SCALE_VOLTAGE_MIN.value, tol.SCALE_VOLTAGE_MAX.value)),
    tc.CORRECTION_ANGLE.value: (FloatValidator, ReadingLimits(tol.CORRECTION_ANGLE_MIN.value, tol.CORRECTION_ANGLE_MAX.value)),
    tc.TEMPERATURE.value: (FloatValidator, ReadingLimits(None, None)),
    tc.PERSISTS.value: (WordMatchValidator, WordMatch("Pass",)),
}


class CellLocation:
    def __init__(self, row: int, col: int):
        if row < 0:
            raise ValueError(f"value {row} given for row must be 0 or greater")

        if col < 0:
            raise ValueError(f"value {col} given for col must be 0 or greater")

        self._row = row
        self._col = col

    @property
    def row(self):
        return self._row

    @property
    def col(self):
        return self._col


class SensorTableViewUpdater:
    def __init__(self, table: QTableWidget, get_temp_ref: Callable):
        self._logger = logging.getLogger(__name__)
        self._table = table
        self._get_temp_ref = get_temp_ref

    def update_from_model(self, sensors: Tuple[Sensor, ...]) -> None:
        for row, sensor in enumerate(sensors):
            for column in range(lwt.TableColumn.RSSI.value, lwt.TableColumn.FAULT_CURRENT.value + 1):
                if column == lwt.TableColumn.FAULT_CURRENT.value:
                    self._update_combo_box(CellLocation(row, lwt.TableColumn.FAULT_CURRENT.value),
                                           sensor.fault_current)
                elif column == lwt.TableColumn.CALIBRATION.value:
                    self._update_combo_box(CellLocation(row, lwt.TableColumn.CALIBRATION.value),
                                           sensor.calibrated)
                else:
                    reading = sensor.__getattribute__(_DATA_IN_TABLE_ORDER[column - 1])
                    self._table.item(row, column).setText(reading)
                    validated_item = self._validate_reading(reading, row, column)
                    self._table.setItem(row, column, validated_item)

    def _update_combo_box(self, cell_location: CellLocation, text: str) -> None:
        def _determine_index(result: str) -> int:
            indexes = {"Pass": 1, "Fail": 2}
            return indexes.get(result, 0)

        self._table.cellWidget(cell_location.row, cell_location.col).setCurrentIndex(_determine_index(text))

    def _validate_reading(self, reading, row, column: int) -> QTableWidgetItem:
        """Validates reading and returns a new QTableWidgetItem with its background colored to indicate pass or fail."""
        assert tc.RSSI.value <= column <= tc.FAULT_CURRENT.value, f"invalid column: {column} not in range"
        validator, limits = validators_by_column[column]
        if validator:
            if column == tc.TEMPERATURE.value:
                brush = self._get_temperature_brush(reading, validator, float(self._get_temp_ref()))
            else:
                brush = validator.get_brush(validator.validate(reading, limits))

            highlighted_item = self._create_highlighted_item(brush, self._table.item(row, column))
            return highlighted_item

    @staticmethod
    def _get_temperature_brush(reading, validator, temp_ref: float) -> QBrush:
        tolerances = temp_ref - tol.TEMPERATURE_DELTA.value, temp_ref + tol.TEMPERATURE_DELTA.value
        pass_fail = validator.validate(reading, tolerances)
        return validator.get_brush(pass_fail)

    @staticmethod
    def _create_highlighted_item(color: QBrush, item: QTableWidgetItem) -> QTableWidgetItem:
        """Clones item and changes its background color to indicate pass or fail."""
        new_item = item.clone()
        new_item.setBackground(color)
        return new_item
