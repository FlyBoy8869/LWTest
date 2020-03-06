from typing import Callable

import LWTest.LWTConstants as LWT

HIGH_MINS = (LWT.Tolerance.HIGH_VOLTAGE_MIN.value,
             LWT.Tolerance.HIGH_CURRENT_MIN.value,
             LWT.Tolerance.HIGH_POWER_MIN.value)

HIGH_MAXS = (LWT.Tolerance.HIGH_VOLTAGE_MAX.value,
             LWT.Tolerance.HIGH_CURRENT_MAX.value,
             LWT.Tolerance.HIGH_POWER_MAX.value)

LOW_MINS = (LWT.Tolerance.LOW_VOLTAGE_MIN.value,
            LWT.Tolerance.LOW_CURRENT_MIN.value,
            LWT.Tolerance.LOW_POWER_MIN.value)

LOW_MAXS = (LWT.Tolerance.LOW_VOLTAGE_MAX.value,
            LWT.Tolerance.LOW_CURRENT_MAX.value,
            LWT.Tolerance.LOW_POWER_MAX.value)

SCALE_MINS = (LWT.Tolerance.SCALE_CURRENT_MIN.value,
              LWT.Tolerance.SCALE_VOLTAGE_MIN.value,
              LWT.Tolerance.CORRECTION_ANGLE_MIN.value)

SCALE_MAXS = (LWT.Tolerance.SCALE_CURRENT_MAX.value,
              LWT.Tolerance.SCALE_VOLTAGE_MAX.value,
              LWT.Tolerance.CORRECTION_ANGLE_MAX.value)

HIGH_COLS = (LWT.TableColumn.HIGH_VOLTAGE.value,
             LWT.TableColumn.HIGH_CURRENT.value,
             LWT.TableColumn.HIGH_REAL_POWER.value)

LOW_COLS = (LWT.TableColumn.LOW_VOLTAGE.value,
            LWT.TableColumn.LOW_CURRENT.value,
            LWT.TableColumn.LOW_REAL_POWER.value)

SCALE_COLS = (LWT.TableColumn.SCALE_CURRENT.value,
              LWT.TableColumn.SCALE_VOLTAGE.value,
              LWT.TableColumn.CORRECTION_ANGLE.value)


def validate_high_voltage_readings(pass_func: Callable, fail_func: Callable, readings: tuple):
    _validate_readings(pass_func, fail_func, _validate_sensor_readings, HIGH_MINS, HIGH_MAXS, HIGH_COLS, readings)


def validate_low_voltage_readings(pass_func: Callable, fail_func: Callable, readings: tuple):
    _validate_readings(pass_func, fail_func, _validate_sensor_readings, LOW_MINS, LOW_MAXS, LOW_COLS, readings)


def validate_scale_n_angle_readings(pass_func: Callable, fail_func: Callable, readings: tuple):
    _validate_readings(pass_func, fail_func, _validate_sensor_readings, SCALE_MINS, SCALE_MAXS, SCALE_COLS, readings)


def validate_temperature_readings(pass_func: Callable, fail_func: Callable, room_temperature: float, readings: tuple):
    for index, temperature in enumerate(readings):
        if temperature == 'NA':
            continue
        if abs(float(temperature) - room_temperature) > LWT.Tolerance.TEMPERATURE_DELTA.value:
            fail_func(index, LWT.TableColumn.TEMPERATURE.value)
        else:
            pass_func(index, LWT.TableColumn.TEMPERATURE.value)


def _validate_readings(pass_func: Callable, fail_func: Callable, validator: Callable, tol_mins: tuple, tol_maxs: tuple,
                       cols, readings: tuple):
    for sensor_index, sensor_readings in enumerate(readings):
        if sensor_readings[0] == 'NA':
            continue

        readings_as_floats = tuple([float(reading.replace(",", "")) for reading in sensor_readings])

        validator(readings_as_floats, sensor_index, cols, tol_mins, tol_maxs, pass_func, fail_func)


def _validate_sensor_readings(readings: tuple, row: int, cols, tol_mins, tol_maxs, pass_func: Callable, fail_func: Callable):
    voltage: float = readings[0]
    current: float = readings[1]
    power: float = readings[2]

    _validate(voltage, tol_mins[0], tol_maxs[0], row, cols[0], pass_func, fail_func)

    _validate(current, tol_mins[1], tol_maxs[1], row, cols[1], pass_func, fail_func)

    _validate(power, tol_mins[2], tol_maxs[2], row, cols[2], pass_func, fail_func)


def _validate(reading: float, min: float, max: float, row: int, column: int, pass_func: Callable, fail_func: Callable):
    if min >= reading or max <= reading:
        fail_func(row, column)
    else:
        pass_func(row, column)