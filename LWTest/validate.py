from typing import Callable

from LWTest.constants import lwt

_HIGH_MINS = (lwt.Tolerance.HIGH_VOLTAGE_MIN.value,
              lwt.Tolerance.HIGH_CURRENT_MIN.value,
              lwt.Tolerance.HIGH_POWER_MIN.value)

_HIGH_MAXS = (lwt.Tolerance.HIGH_VOLTAGE_MAX.value,
              lwt.Tolerance.HIGH_CURRENT_MAX.value,
              lwt.Tolerance.HIGH_POWER_MAX.value)

_LOW_MINS = (lwt.Tolerance.LOW_VOLTAGE_MIN.value,
             lwt.Tolerance.LOW_CURRENT_MIN.value,
             lwt.Tolerance.LOW_POWER_MIN.value)

_LOW_MAXS = (lwt.Tolerance.LOW_VOLTAGE_MAX.value,
             lwt.Tolerance.LOW_CURRENT_MAX.value,
             lwt.Tolerance.LOW_POWER_MAX.value)

_SCALE_MINS = (lwt.Tolerance.SCALE_CURRENT_MIN.value,
               lwt.Tolerance.SCALE_VOLTAGE_MIN.value,
               lwt.Tolerance.CORRECTION_ANGLE_MIN.value)

_SCALE_MAXS = (lwt.Tolerance.SCALE_CURRENT_MAX.value,
               lwt.Tolerance.SCALE_VOLTAGE_MAX.value,
               lwt.Tolerance.CORRECTION_ANGLE_MAX.value)

_HIGH_COLS = (lwt.TableColumn.HIGH_VOLTAGE.value,
              lwt.TableColumn.HIGH_CURRENT.value,
              lwt.TableColumn.HIGH_REAL_POWER.value)

_LOW_COLS = (lwt.TableColumn.LOW_VOLTAGE.value,
             lwt.TableColumn.LOW_CURRENT.value,
             lwt.TableColumn.LOW_REAL_POWER.value)

_SCALE_COLS = (lwt.TableColumn.SCALE_CURRENT.value,
               lwt.TableColumn.SCALE_VOLTAGE.value,
               lwt.TableColumn.CORRECTION_ANGLE.value)


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
            if temperature == lwt.NO_DATA:
                continue

            if abs(float(temperature) - room_temperature) > lwt.Tolerance.TEMPERATURE_DELTA.value:
                self._failing(index, lwt.TableColumn.TEMPERATURE.value)
            else:
                self._passing(index, lwt.TableColumn.TEMPERATURE.value)

    def _validate_readings(self, tol_min: tuple, tol_max: tuple, cols: tuple, readings: tuple) -> None:
        for sensor_index, sensor_readings in enumerate(readings):
            if sensor_readings[0] == lwt.NO_DATA:
                continue

            readings_as_floats = tuple([float(reading.replace(",", "")) for reading in sensor_readings])

            for index, reading in enumerate(readings_as_floats):
                self._validate(readings_as_floats[index], tol_min[index], tol_max[index], sensor_index, cols[index])

    def _validate(self, reading: float, minimum: float, maximum: float, row: int, column: int) -> None:
        if minimum >= reading or maximum <= reading:
            self._failing(row, column)
        else:
            self._passing(row, column)
