# sensor.py
from typing import Optional


class Sensor:
    def __init__(self, line_position: int, serial_number: str):
        self.line_position = line_position
        self.serial_number = serial_number

        self.result = "Not Tested"
        self.rssi = "Not Linked"
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

    def get_serial_numbers(self) -> tuple:
        return tuple([sensor.serial_number for sensor in self._log.values()])

    # def get_line_position(self, serial_number: str) -> int:
    #     return self._find_sensor(serial_number).line_position

    def get_persistence_values_for_comparison(self):
        values = []
        for sensor in self._log.values():
            values.append((sensor.scale_current, sensor.scale_voltage, sensor.correction_angle))

        return tuple(values)

    def get_sensor_by_line_position(self, line_position):
        for sensor in self._log.values():
            if sensor.line_position == line_position:
                return sensor

        return None

    def get_test_results(self) -> tuple:
        return tuple([sensor.result for sensor in self._log.values()])

    def is_empty(self):
        return len(self._log) == 0

    def is_tested(self, serial_number: str) -> bool:
        return self._find_sensor(serial_number).tested

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
        return f"SensorLog({self.get_serial_numbers()})"


if __name__ == '__main__':
    numbers = ['9800001', '9800002', '9800003', '9800004', '9800005', '9800006']
    sensor_log = SensorLog()
    sensor_log.append_all(numbers)

    assert len(sensor_log) == 6, "sensor_log should have 6 elements"
    assert sensor_log.get_serial_numbers() == tuple(numbers), "serial numbers don't match"
    assert sensor_log.get_line_position(numbers[3]) == 3, "incorrect line position"
