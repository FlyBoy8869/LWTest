from typing import Callable, Tuple, Union, cast

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


def _no_op():
    # a no op with_marker
    pass


class Validator:
    """Validate sensor readings."""

    def __init__(self, passing: Callable, failing: Callable) -> None:
        """passing: Function to call when reading passes.
           failing: Function to call when reading fails."""

        self._passing_marker = passing
        self._failing_marker = failing
        self._no_marker = lambda row, col: _no_op()

    def validate_high_voltage_readings(self, readings: tuple) -> None:
        assert all(readings), f"sequence can not contain an empty string: {readings}"
        self._validate_readings(_HIGH_MINS, _HIGH_MAXS, _HIGH_COLS, readings)

    def validate_low_voltage_readings(self, readings: tuple) -> None:
        assert all(readings), f"sequence can not contain an empty string: {readings}"
        self._validate_readings(_LOW_MINS, _LOW_MAXS, _LOW_COLS, readings)

    def validate_scale_n_angle_readings(self, readings: tuple) -> None:
        assert all(readings), f"sequence can not contain an empty string: {readings}"
        self._validate_readings(_SCALE_MINS, _SCALE_MAXS, _SCALE_COLS, readings)

    def validate_temperature_readings(self, room_temperature: float, readings: tuple) -> None:
        assert all(readings), f"sequence can not contain an empty string: {readings}"
        for index, temperature in enumerate(readings):
            self._mark_cell_good_or_bad(
                at_cell_row=index,
                and_cell_col=lwt.TableColumn.TEMPERATURE.value,
                with_marker=self._choose_marker(
                    self._check_value(
                        temperature,
                        room_temperature - lwt.Tolerance.TEMPERATURE_DELTA.value,
                        room_temperature + lwt.Tolerance.TEMPERATURE_DELTA.value,
                        self._in_tolerance
                    ),
                    good_marker=self._passing_marker,
                    bad_marker=self._failing_marker,
                    no_marker=self._no_marker
                )
            )

    def _validate_readings(self,
                           tol_min: Tuple[float, ...],
                           tol_max: Tuple[float, ...],
                           cols: Tuple[int, ...],
                           readings: Tuple[Tuple, ...]) -> None:

        for sensor_index, sensor_readings in enumerate(readings):
            for index, reading in enumerate(sensor_readings):
                self._mark_cell_good_or_bad(
                    at_cell_row=sensor_index,
                    and_cell_col=cols[index],
                    with_marker=self._choose_marker(
                        self._check_value(
                            self._remove_comma_from(reading),
                            tol_min[index],
                            tol_max[index],
                            self._in_tolerance
                        ),
                        good_marker=self._passing_marker,
                        bad_marker=self._failing_marker,
                        no_marker=self._no_marker
                    )
                )

    @staticmethod
    def _mark_cell_good_or_bad(*, at_cell_row: int, and_cell_col: int, with_marker: Callable) -> None:
        with_marker(at_cell_row, and_cell_col)

    @staticmethod
    def _choose_marker(result: str, *, good_marker, bad_marker, no_marker) -> Callable:
        assert result in ["IN", "OUT", "NAN"], "result must be one of 'IN', 'OUT' or 'NAN'"

        markers = {"IN": good_marker, "OUT": bad_marker, "NAN": no_marker}
        return markers[result]

    @staticmethod
    def _check_value(reading: str, minimum: float, maximum: float, verifier: Callable) -> str:
        if reading == lwt.NO_DATA:
            return "NAN"
        return "IN" if verifier(float(reading), minimum, maximum) else "OUT"

    @staticmethod
    def _remove_comma_from(reading: str) -> str:
        return reading.replace(",", "")

    @staticmethod
    def _in_tolerance(reading: float, minimum: float, maximum: float) -> bool:
        if minimum < reading < maximum:
            return True
        return False
