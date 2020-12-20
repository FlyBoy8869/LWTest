from unittest import TestCase

import LWTest.sensor as sensor


class TestSensorLogGetSensorByPhase(TestCase):
    def setUp(self) -> None:
        self.sensor_log = sensor.SensorLog()
        self.sensor_log.create_all(("9800001", "9800002", "9800003", "9800004", "9800005",))

    def test_get_sensor_by_phase(self):
        phase = 2
        unit: sensor.Sensor = self.sensor_log.get_sensor_by_phase(phase)
        self.assertIsInstance(unit, sensor.Sensor)
        self.assertEqual("9800003", unit.serial_number)

    def test_get_sensor_by_phase__find_None(self):
        phase = 5
        unit: sensor.Sensor = self.sensor_log.get_sensor_by_phase(phase)
        self.assertEqual(None, unit)

    def test_get_sensor_by_phase__raise_assertion_error(self):
        phase = 7
        self.assertRaises(AssertionError, self.sensor_log.get_sensor_by_phase, phase)
