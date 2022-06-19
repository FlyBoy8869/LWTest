# sensor.py
import logging
from dataclasses import dataclass, field
from functools import singledispatchmethod
from typing import List, Optional, Tuple, cast

from PyQt6.QtCore import QObject, pyqtSignal

from LWTest.collector.common.constants import ReadingType


@dataclass
class Sensor:
    _phase: int
    _serial_number: str
    result: str = field(init=False, default="NA")
    rssi: str = field(init=False, default="NA")
    firmware_version: str = field(init=False, default="NA")
    reporting_data: str = field(init=False, default="NA")
    calibrated: str = field(init=False, default="NA")
    high_voltage: str = field(init=False, default="NA")
    high_current: str = field(init=False, default="NA")
    high_power_factor: str = field(init=False, default="NA")
    high_real_power: str = field(init=False, default="NA")
    low_voltage: str = field(init=False, default="NA")
    low_current: str = field(init=False, default="NA")
    low_power_factor: str = field(init=False, default="NA")
    low_real_power: str = field(init=False, default="NA")
    scale_current: str = field(init=False, default="NA")
    scale_voltage: str = field(init=False, default="NA")
    correction_angle: str = field(init=False, default="NA")
    temperature: str = field(init=False, default="NA")
    fault_current: str = field(init=False, default="NA")
    persists: str = field(init=False, default="NA")

    @property
    def advance_readings(self) -> Tuple[str, ...]:
        return self.scale_current, self.scale_voltage, self.correction_angle

    @property
    def linked(self):
        try:
            return int(self.rssi) in [-i for i in range(120)]
        except ValueError:
            return False

    @property
    def phase(self):
        return self._phase

    @property
    def serial_number(self):
        return self._serial_number

    @property
    def reporting(self):
        return self.reporting_data == "Pass"

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)


_sensor_attributes = {
    ReadingType.HIGH_VOLTAGE: "high_voltage",
    ReadingType.HIGH_CURRENT: "high_current",
    ReadingType.HIGH_POWER_FACTOR: "high_power_factor",
    ReadingType.HIGH_REAL_POWER: "high_real_power",
    ReadingType.LOW_VOLTAGE: "low_voltage",
    ReadingType.LOW_CURRENT: "low_current",
    ReadingType.LOW_POWER_FACTOR: "low_power_factor",
    ReadingType.LOW_REAL_POWER: "low_real_power",
    ReadingType.SCALE_CURRENT: "scale_current",
    ReadingType.SCALE_VOLTAGE: "scale_voltage",
    ReadingType.CORRECTION_ANGLE: "correction_angle",
    ReadingType.TEMPERATURE: "temperature",
    ReadingType.PERSISTS: "persists",
    ReadingType.RSSI: "rssi",
    ReadingType.FIRMWARE: "firmware_version",
    ReadingType.REPORTING: "reporting_data",
    ReadingType.CALIBRATED: "calibrated",
    ReadingType.FAULT_CURRENT: "fault_current",
}


class SensorLog(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._log_by_serial_number = {}
        self._log_by_phase = {}
        self._room_temperature: str = "21.7"
        self._high_voltage_reference = ("", "", "", "")
        self._low_voltage_reference = ("", "", "", "")

    @property
    def have_references(self):
        return all(self._high_voltage_reference) and all(self._low_voltage_reference)

    @property
    def linked(self):
        return [sensor.serial_number for sensor in self if sensor.linked]

    @property
    def references(self):
        return self._high_voltage_reference, self._low_voltage_reference

    @references.setter
    def references(self, values):
        high_refs, low_refs = values
        self._high_voltage_reference = high_refs
        self._low_voltage_reference = low_refs

    @property
    def room_temperature(self):
        return self._room_temperature

    @room_temperature.setter
    def room_temperature(self, value: float):
        self._room_temperature = f"{value:.1f}"
        self._logger.debug(f"room temperature reference set to: {self._room_temperature}")

    @property
    def unlinked(self):
        return [sensor.serial_number for sensor in self if not sensor.linked]

    def create_all(self, iterable):
        self._clear()
        for index, number in enumerate(iterable):
            sensor = Sensor(index, number)
            self._append(sensor)
            self._logger.debug(f"added sensor {number} to sensor log")

    def get_serial_numbers_as_tuple(self) -> Tuple[str, ...]:
        return tuple(cast(List[str], [sensor.serial_number for sensor in self._log_by_serial_number.values()]))

    def get_serial_numbers_as_list(self) -> List[str]:
        return [sensor.serial_number for sensor in self._log_by_serial_number.values()]

    def get_advanced_readings(self) -> Tuple[Tuple[str], ...]:
        return tuple([sensor.advance_readings for sensor in self._log_by_serial_number.values()])

    def get_sensor_by_phase(self, phase: int) -> Optional[Sensor]:
        assert phase in {0, 1, 2, 3, 4, 5}, f"'{phase}' is invalid, must be 0 - 5"
        return self._log_by_phase.get(phase, None)

    def get_sensors(self) -> Tuple[Sensor]:
        return tuple([cast(Sensor, sensor) for sensor in self._log_by_serial_number.values()])

    def record_calibration_results(self, result: str, index: int):
        self.get_sensor_by_phase(index).calibrated = result
        # noinspection PyUnresolvedReferences
        self.changed.emit()

    def record_fault_current_results(self, result: str, index: int):
        self.get_sensor_by_phase(index).fault_current = result
        # noinspection PyUnresolvedReferences
        self.changed.emit()

    @singledispatchmethod
    def save(self, values, kind, _: str = ""):
        raise NotImplementedError("default for use with @singledispatchmethod")

    @save.register
    def _(self, values: tuple, reading_type: ReadingType, _: str = ""):
        self._save(values, _sensor_attributes[reading_type])

    @save.register
    def _(self, value: str, reading_type: ReadingType, serial_number: str = ""):
        assert serial_number != "", "missing serial_number"

        unit: Sensor = self._log_by_serial_number[serial_number]
        setattr(unit, _sensor_attributes[reading_type], value)
        # 'change' signal is not emitted here for performance reasons
        self._logger.debug(f"set sensor({unit.serial_number}).{_sensor_attributes[reading_type]} = {value}")

    def _save(self, values, attribute):
        for index, unit in enumerate(self):
            if unit.linked:
                setattr(unit, attribute, values[index])
                self._logger.debug(f"set sensor({unit.serial_number}).{attribute} = {values[index]}")
        # noinspection PyUnresolvedReferences
        self.changed.emit()

    # "private" interface
    def _append(self, sensor: Sensor):
        self._log_by_serial_number[sensor.serial_number] = sensor
        self._log_by_phase[sensor.phase] = sensor

    def _clear(self):
        self._log_by_serial_number.clear()
        self._log_by_phase.clear()

    def __getitem__(self, key):
        return self._log_by_serial_number[key]

    def __iter__(self):
        return iter(self._log_by_serial_number.values())

    def __repr__(self):
        return f"SensorLog({self.get_serial_numbers_as_tuple()})"
