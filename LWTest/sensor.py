# sensor.py
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, cast

from PyQt5.QtCore import QObject, pyqtSignal

import LWTest.constants.lwt_constants as lwt


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
    def phase(self):
        return self._phase

    @property
    def serial_number(self):
        return self._serial_number

    @property
    def linked(self):
        try:
            return int(self.rssi) in [-i for i in range(0, 120)]
        except ValueError:
            return False


class SensorLog(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._log_by_serial_number = {}
        self._log_by_phase = {}
        self._room_temperature: str = "21.7"
        self._high_voltage_reference = ("", "", "", "")
        self._low_voltage_reference = ("", "", "", "")

    @property
    def have_references(self):
        if not all(self._high_voltage_reference)\
         or not all(self._low_voltage_reference):
            return False

        return True

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
    def room_temperature(self, value):
        self._room_temperature = f"{value:.1f}"
        print(f"room temperature = {self._room_temperature}")

    def create_all(self, iterable):
        self._clear()
        for index, number in enumerate(iterable):
            self._append(Sensor(index, number))

    def get_serial_numbers_as_tuple(self) -> Tuple[str]:
        return tuple(
            cast(
                List[str],
                [sensor.serial_number
                 for sensor in self._log_by_serial_number.values()]
            )
        )

    def get_serial_numbers_as_list(self) -> List[str]:
        return [sensor.serial_number
                for sensor in self._log_by_serial_number.values()]

    def get_advanced_readings(self):
        values = []
        for sensor in self._log_by_serial_number.values():
            values.append(
                (sensor.scale_current,
                 sensor.scale_voltage,
                 sensor.correction_angle)
            )

        return tuple(values)

    def get_sensor_by_phase(self, phase: int) -> Optional[Sensor]:
        assert phase in [0, 1, 2, 3, 4, 5],\
            f"'{phase}' is invalid, must be 0 - 5"
        return self._log_by_phase.get(phase, None)

    def get_sensors(self) -> Tuple[Sensor]:
        return tuple(
            [
                cast(Sensor, sensor)
                for sensor in self._log_by_serial_number.values()
            ]
        )

    def record_reporting_data(self, line_position: int, reporting: str):
        self.get_sensor_by_phase(line_position).reporting_data = reporting

    def record_sensor_calibration(self, result, index):
        self.get_sensor_by_phase(index).calibrated = result

    def record_fault_current_readings(self, value: str):
        unit: Sensor

        for unit in self:
            if unit.linked:
                unit.fault_current = value

    def record_firmware_version(self, phase, version):
        self.get_sensor_by_phase(phase).firmware_version = version

    def record_rssi_readings(self, serial_number, rssi):
        self._log_by_serial_number[serial_number].rssi = rssi

    def record_non_linked_sensors(self, serial_numbers):
        for serial_number in serial_numbers:
            self._log_by_serial_number[serial_number].rssi = lwt.NO_DATA

    record_attributes = {
        "HIGH_VOLTAGE": "high_voltage",
        "HIGH_CURRENT": "high_current",
        "HIGH_POWER_FACTOR": "high_power_factor",
        "HIGH_REAL_POWER": "high_real_power",
        "LOW_VOLTAGE": "low_voltage",
        "LOW_CURRENT": "low_current",
        "LOW_POWER_FACTOR": "low_power_factor",
        "LOW_REAL_POWER": "low_real_power",
        "SCALE_CURRENT": "scale_current",
        "SCALE_VOLTAGE": "scale_voltage",
        "CORRECTION_ANGLE": "correction_angle",
        "TEMPERATURE": "temperature",
        "PERSISTS": "persists",
    }

    def save_readings(self, kind: str, values: Tuple[str]):
        self._save(self.record_attributes[kind], values)

    def _save(self, attribute, values):
        for index, unit in enumerate(self):
            if unit.linked:
                setattr(unit, attribute, values[index])

        self.changed.emit()

    # "private" interface
    def _append(self, sensor: Sensor):
        self._log_by_serial_number[sensor.serial_number] = sensor
        self._log_by_phase[sensor.phase] = sensor

    def _clear(self):
        self._log_by_serial_number.clear()

    def __getitem__(self, key):
        return self._log_by_serial_number[key]

    def __iter__(self):
        return iter(self._log_by_serial_number.values())

    def __repr__(self):
        return f"SensorLog({self.get_serial_numbers_as_tuple()})"
