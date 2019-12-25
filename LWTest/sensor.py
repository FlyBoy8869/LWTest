# sensor.py
from typing import Optional


class Sensor:
    def __init__(self, line_position, serial_number):
        self.line_position = line_position
        self.serial_number = serial_number
        self.tested = False
        self.result = "Not Tested"
        self.rssi = None
        self.software_version = 0x0
        self.reporting_data = "False"
        # self.line_skip_count = 0


class SensorLog:
    def __init__(self):
        self.log = dict()

    def append(self, sensor: Sensor):
        self.log[(sensor.line_position, sensor.serial_number)] = sensor

    def append_all(self, iterable):
        self.log.clear()
        for index, number in enumerate(iterable):
            self.append(Sensor(index, number))

    def clear(self):
        self.log.clear()

    def count(self):
        return len(self.log)

    def get_actual_count(self):
        return len([sn for sn in self.get_serial_numbers() if sn != "0"])

    def get_serial_numbers(self) -> tuple:
        return tuple([sensor.serial_number for sensor in self.log.values()])

    def get_line_position_of_sensor(self, serial_number: str) -> int:
        return self._find_sensor_by_serial_number(serial_number).line_position

    def get_test_results(self) -> tuple:
        return tuple([sensor.result for sensor in self.log.values()])

    def is_empty(self):
        return len(self.log) == 0

    def is_tested(self, serial_number: str) -> bool:
        return self._find_sensor_by_serial_number(serial_number).tested

    def set_test_result(self, serial_number: str, result: str):
        sensor = self._find_sensor_by_serial_number(serial_number)
        sensor.result = result
        sensor.tested = True

    def _find_sensor_by_serial_number(self, serial_number) -> (Sensor, Optional):
        for sensor in self.log.values():
            if sensor.serial_number == serial_number:
                return sensor
        return None
