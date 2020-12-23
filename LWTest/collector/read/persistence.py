from typing import Tuple

from PyQt5.QtCore import QObject, pyqtSignal
from selenium import webdriver

from LWTest.collector.common import helpers
from LWTest.collector.common.constants import ADVANCED_CONFIG_SELECTOR, ReadingType


class PersistenceComparator(QObject):
    persisted = pyqtSignal(tuple, int)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def compare(self, saved_readings, url: str, driver: webdriver.Chrome):
        driver.get(url)
        columns = helpers.get_columns(driver)
        self.persisted.emit(
            self._compare(
                saved_readings,
                self._live_readings(columns, driver)
            ),
            ReadingType.PERSISTS
        )
        self.finished.emit()

    def _live_readings(self, sensor_count: int, driver: webdriver.Chrome):
        return self._reading_element_values(
            helpers.get_elements(ADVANCED_CONFIG_SELECTOR, driver),
            sensor_count
        )

    def _reading_element_values(self, reading_elements, count: int):
        return tuple(
            zip(
                self._get_scale_current_values(reading_elements, count),
                self._get_scale_voltage_values(reading_elements, count),
                self._get_correction_angle_values(reading_elements, count)
            )
        )

    def _get_scale_current_values(self, elements, count: int):
        return self._get_values(elements, start=0, stop=count)

    def _get_scale_voltage_values(self, elements, count: int):
        return self._get_values(elements, start=count, stop=count * 2)

    def _get_correction_angle_values(self, elements, count: int):
        return self._get_values(elements, start=count * 4, stop=count * 4 + count)

    @staticmethod
    def _get_values(elements, *, start, stop):
        return [reading.get_attribute("value") for reading in elements[start:stop]]

    @staticmethod
    def _compare(saved_readings, live_readings) -> Tuple[str]:
        persistence_results = ["Pass"] * len(saved_readings)

        for sensor_index, sensor_readings in enumerate(saved_readings):
            if live_readings[sensor_index] != sensor_readings:
                persistence_results[sensor_index] = "Fail"

        return tuple(persistence_results)
