# sensor.py
from typing import Optional, List, Tuple, cast


class Sensor:
    def __init__(self, phase: int, serial_number: str):
        self.phase: int = phase
        self.serial_number: str = serial_number

        self.result = "Not Tested"
        self.rssi = "NA"
        self.firmware_version = "NA"
        self.reporting_data = "NA"
        self.calibrated = "NA"
        self.high_voltage = "NA"
        self.high_current = "NA"
        self.high_power_factor = "NA"
        self.high_real_power = "NA"
        self.low_voltage = "NA"
        self.low_current = "NA"
        self.low_power_factor = "NA"
        self.low_real_power = "NA"
        self.temperature = "NA"
        self.fault_current = "NA"
        self.scale_current = "NA"
        self.scale_voltage = "NA"
        self.correction_angle = "NA"
        self.persists = "NA"

    @property
    def linked(self):
        return self.rssi != "Not Linked"

    def __repr__(self):
        r = (f"Sensor(serial_number={self.serial_number}, rssi={self.rssi}, "
             f"firmware_version={self.firmware_version}, "
             f"reporting_data={self.reporting_data}, calibrated={self.calibrated}, high_voltage={self.high_voltage}, "
             f"high_current={self.high_current}, high_power_factor={self.high_power_factor}, "
             f"high_real_power={self.high_real_power}, low_voltage={self.low_voltage}, "
             f"low_current={self.low_current}, low_power_factor={self.low_power_factor}, "
             f"low_real_power={self.low_real_power}, temperature={self.temperature}, "
             f"fault_current='{self.fault_current}', scale_current={self.scale_current}, "
             f"scale_voltage={self.scale_voltage}, correction_angle={self.correction_angle}, "
             f"persists='{self.persists}'")

        return r


class SensorLog:
    def __init__(self):
        self._log = dict()
        self._room_temperature: str = "21.7"

    @property
    def room_temperature(self):
        return self._room_temperature

    @room_temperature.setter
    def room_temperature(self, value):
        self._room_temperature = f"{value:.1f}"
        print(f"room temperature = {self._room_temperature}")

    def append_all(self, iterable):
        self._clear()
        for index, number in enumerate(iterable):
            self._append(Sensor(index, number))

    def get_serial_numbers_as_tuple(self) -> Tuple[str]:
        return tuple(cast(List[str], [sensor.serial_number for sensor in self._log.values()]))

    def get_serial_numbers_as_list(self) -> List[str]:
        return [sensor.serial_number for sensor in self._log.values()]

    def get_advanced_readings(self):
        values = []
        for sensor in self._log.values():
            values.append((sensor.scale_current, sensor.scale_voltage, sensor.correction_angle))

        return tuple(values)

    def get_sensor_by_phase(self, phase):
        for sensor in self._log.values():
            if sensor.phase == phase:
                return sensor

        return None

    def get_sensors(self) -> Tuple[Sensor]:
        return tuple([cast(Sensor, sensor) for sensor in self._log.values()])

    def get_test_results(self) -> tuple:
        return tuple([sensor.result for sensor in self._log.values()])

    def is_empty(self):
        return len(self._log) == 0

    def is_tested(self, serial_number: str) -> bool:
        return self._find_sensor(serial_number).tested

    def record_reporting_data(self, line_position: int, reporting: str):
        self.get_sensor_by_phase(line_position).reporting_data = reporting

    def record_sensor_calibration(self, result, index):
        self.get_sensor_by_phase(index).calibrated = result

    def record_high_voltage_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.high_voltage = values[index].replace(',', '')

    def record_high_current_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.high_current = values[index]

    def record_high_power_factor_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.high_power_factor = values[index]

    def record_high_real_power_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.high_real_power = values[index]

    def record_low_voltage_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.low_voltage = values[index].replace(',', '')

    def record_low_current_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.low_current = values[index]

    def record_low_power_factor_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.low_power_factor = values[index]

    def record_low_real_power_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.low_real_power = values[index]

    def record_temperature_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.temperature = values[index]

    def record_fault_current_readings(self, value: str):
        unit: Sensor

        for unit in self:
            if unit.linked:
                unit.fault_current = value

    def record_scale_current_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.scale_current = values[index]

    def record_scale_voltage_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.scale_voltage = values[index]

    def record_correction_angle_readings(self, values: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.correction_angle = values[index]

    def record_persistence_readings(self, value: list):
        unit: Sensor

        for index, unit in enumerate(self):
            if unit.linked:
                unit.persists = value[index]

    def record_firmware_version(self, phase, version):
        self.get_sensor_by_phase(phase).firmware_version = version

    def record_rssi_readings(self, serial_number, rssi):
        self._log[serial_number].rssi = rssi

    def record_non_linked_sensors(self, serial_numbers):
        for serial_number in serial_numbers:
            self._log[serial_number].rssi = "Not Linked"

    def set_test_result(self, serial_number: str, result: str):
        sensor = self._find_sensor(serial_number)
        sensor.result = result
        sensor.tested = True

    # "private" interface
    def _append(self, sensor: Sensor):
        self._log[sensor.serial_number] = sensor

    def _clear(self):
        self._log.clear()

    def _find_sensor(self, serial_number) -> (Sensor, Optional):
        return self._log[serial_number]

    def __getitem__(self, key):
        return self._log[key]

    def __iter__(self):
        return iter(self._log.values())

    def __len__(self):
        return len(self._log)

    def __repr__(self):
        return f"SensorLog({self.get_serial_numbers_as_tuple()})"


if __name__ == '__main__':
    numbers = ['9800001', '9800002', '9800003', '9800004', '9800005', '9800006']
    sensor_log = SensorLog()
    sensor_log.append_all(numbers)

    assert len(sensor_log) == 6, "sensor_log should have 6 elements"
    assert sensor_log.get_serial_numbers_as_tuple() == tuple(numbers), "serial numbers don't match"
