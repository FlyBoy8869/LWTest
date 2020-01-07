# sensor.py
from typing import Optional


class Sensor:
    def __init__(self, line_position, serial_number):
        self.line_position = line_position
        self.serial_number = serial_number
        self.tested = False
        self.result = "Not Tested"
        self.rssi = "Not Linked"
        self.firmware_version = ""
        self.reporting_data = ""
        self.calibrated = ""
        self.high_voltage = ""
        self.high_current = ""
        self.high_power_factor = ""
        self.high_real_power = ""
        self.low_voltage = ""
        self.low_current = ""
        self.low_power_factor = ""
        self.low_real_power = ""
        self.temperature = ""
        self.fault_current = ""
        self.scale_current = ""
        self.scale_voltage = ""
        self.correction_angle = ""
        self.persists = ""

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

    def append_all(self, iterable):
        self._clear()
        for index, number in enumerate(iterable):
            self._append(Sensor(index, number))

    def get_serial_numbers(self) -> tuple:
        return tuple([sensor.serial_number for sensor in self._log.values()])

    def get_line_position_of_sensor(self, serial_number: str) -> int:
        return self._find_sensor(serial_number).line_position

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
    numbers = ['9801010', '9802020', '9803030', '9804040', '9805050', '9806060']
    sensor_log = SensorLog()
    sensor_log.append_all(numbers)

    assert len(sensor_log) == 6, "sensor_log should have 6 elements"
    assert sensor_log.get_serial_numbers() == tuple(numbers), "serial numbers don't match"
    assert sensor_log.get_line_position_of_sensor(numbers[3]) == 3, "incorrect line position"
