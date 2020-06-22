from typing import Callable

import LWTest.LWTConstants as LWT


_HIGH_MINS = (LWT.Tolerance.HIGH_VOLTAGE_MIN.value,
              LWT.Tolerance.HIGH_CURRENT_MIN.value,
              LWT.Tolerance.HIGH_POWER_MIN.value)

_HIGH_MAXS = (LWT.Tolerance.HIGH_VOLTAGE_MAX.value,
              LWT.Tolerance.HIGH_CURRENT_MAX.value,
              LWT.Tolerance.HIGH_POWER_MAX.value)

_LOW_MINS = (LWT.Tolerance.LOW_VOLTAGE_MIN.value,
             LWT.Tolerance.LOW_CURRENT_MIN.value,
             LWT.Tolerance.LOW_POWER_MIN.value)

_LOW_MAXS = (LWT.Tolerance.LOW_VOLTAGE_MAX.value,
             LWT.Tolerance.LOW_CURRENT_MAX.value,
             LWT.Tolerance.LOW_POWER_MAX.value)

_SCALE_MINS = (LWT.Tolerance.SCALE_CURRENT_MIN.value,
               LWT.Tolerance.SCALE_VOLTAGE_MIN.value,
               LWT.Tolerance.CORRECTION_ANGLE_MIN.value)

_SCALE_MAXS = (LWT.Tolerance.SCALE_CURRENT_MAX.value,
               LWT.Tolerance.SCALE_VOLTAGE_MAX.value,
               LWT.Tolerance.CORRECTION_ANGLE_MAX.value)

_HIGH_COLS = (LWT.TableColumn.HIGH_VOLTAGE.value,
              LWT.TableColumn.HIGH_CURRENT.value,
              LWT.TableColumn.HIGH_REAL_POWER.value)

_LOW_COLS = (LWT.TableColumn.LOW_VOLTAGE.value,
             LWT.TableColumn.LOW_CURRENT.value,
             LWT.TableColumn.LOW_REAL_POWER.value)

_SCALE_COLS = (LWT.TableColumn.SCALE_CURRENT.value,
               LWT.TableColumn.SCALE_VOLTAGE.value,
               LWT.TableColumn.CORRECTION_ANGLE.value)


class Validator:
    """Validate sensor readings."""

    def __init__(self, passing: Callable, failing: Callable) -> None:
        """passing: Function to call when reading passes.
           failing: Function to call when reading fails."""

        self._passing = passing
        self._failing = failing

    def validate_high_voltage_readings(self, readings: tuple) -> None:
        self._validate_readings(_HIGH_MINS, _HIGH_MAXS, _HIGH_COLS, readings)

    def validate_low_voltage_readings(self, readings: tuple) -> None:
        self._validate_readings(_LOW_MINS, _LOW_MAXS, _LOW_COLS, readings)

    def validate_scale_n_angle_readings(self, readings: tuple) -> None:
        self._validate_readings(_SCALE_MINS, _SCALE_MAXS, _SCALE_COLS, readings)

    def validate_temperature_readings(self, room_temperature: float, readings: tuple) -> None:
        for index, temperature in enumerate(readings):
            if temperature == LWT.NO_DATA:
                continue

            if abs(float(temperature) - room_temperature) > LWT.Tolerance.TEMPERATURE_DELTA.value:
                self._failing(index, LWT.TableColumn.TEMPERATURE.value)
            else:
                self._passing(index, LWT.TableColumn.TEMPERATURE.value)

    def _validate_readings(self, tol_min: tuple, tol_max: tuple, cols: tuple, readings: tuple) -> None:
        for sensor_index, sensor_readings in enumerate(readings):
            if sensor_readings[0] == LWT.NO_DATA:
                continue

            readings_as_floats = tuple([float(reading.replace(",", "")) for reading in sensor_readings])

            for index, reading in enumerate(readings_as_floats):
                self._validate(readings_as_floats[index], tol_min[index], tol_max[index], sensor_index, cols[index])

    def _validate(self, reading: float, min: float, max: float, row: int, column: int) -> None:
        if min >= reading or max <= reading:
            self._failing(row, column)
        else:
            self._passing(row, column)
