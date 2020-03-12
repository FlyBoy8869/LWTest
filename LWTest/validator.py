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
    def __init__(self, passing: Callable, failing: Callable):
        self._passing = passing
        self._failing = failing

    def validate_high_voltage_readings(self, readings: tuple):
        self._validate_readings(self._validate_sensor_readings, _HIGH_MINS, _HIGH_MAXS, _HIGH_COLS, readings)

    def validate_low_voltage_readings(self, readings: tuple):
        self._validate_readings(self._validate_sensor_readings, _LOW_MINS, _LOW_MAXS, _LOW_COLS, readings)

    def validate_scale_n_angle_readings(self, readings: tuple):
        self._validate_readings(self._validate_sensor_readings, _SCALE_MINS, _SCALE_MAXS, _SCALE_COLS, readings)

    def validate_temperature_readings(self, room_temperature: float, readings: tuple):
        for index, temperature in enumerate(readings):
            if temperature == 'NA':
                continue
            if abs(float(temperature) - room_temperature) > LWT.Tolerance.TEMPERATURE_DELTA.value:
                self._failing(index, LWT.TableColumn.TEMPERATURE.value)
            else:
                self._passing(index, LWT.TableColumn.TEMPERATURE.value)

    def _validate_readings(self, validator: Callable, tol_mins: tuple, tol_maxs: tuple, cols: tuple, readings: tuple):
        for sensor_index, sensor_readings in enumerate(readings):
            if sensor_readings[0] == 'NA':
                continue

            readings_as_floats = tuple([float(reading.replace(",", "")) for reading in sensor_readings])

            validator(readings_as_floats, sensor_index, cols, tol_mins, tol_maxs)

    def _validate_sensor_readings(self, readings: tuple, row: int, cols, tol_mins, tol_maxs):
        voltage: float = readings[0]
        current: float = readings[1]
        power: float = readings[2]

        self._validate(voltage, tol_mins[0], tol_maxs[0], row, cols[0])

        self._validate(current, tol_mins[1], tol_maxs[1], row, cols[1])

        self._validate(power, tol_mins[2], tol_maxs[2], row, cols[2])

    def _validate(self, reading: float, min: float, max: float, row: int, column: int):
        if min >= reading or max <= reading:
            self._failing(row, column)
        else:
            self._passing(row, column)

