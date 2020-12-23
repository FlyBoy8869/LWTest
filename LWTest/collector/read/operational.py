import logging

from PyQt5.QtCore import pyqtSignal, QObject
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from LWTest.constants import lwt


class Reader(QObject):
    update = pyqtSignal(int, str)
    finished = pyqtSignal()

    ATTRIBUTE = "textContent"
    SELECTOR = ""
    RANGE_ = None
    URL = ""
    WAIT_TIME = 10

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)

    def read(self, phase: int, driver: webdriver.Chrome):
        return self._get_data(phase, driver)

    def _emit_signals(self, phase, data):
        self.update.emit(phase, data)
        self.finished.emit()

    def _get_data(self, phase: int, driver: webdriver.Chrome):
        try:
            elements = self._get_elements(self.SELECTOR, self.RANGE_, driver)
            content = elements[phase].get_attribute(self.ATTRIBUTE)
            return content
        except TimeoutException:
            return lwt.NO_DATA

    def _get_elements(self, selector: str, range_: slice, driver: webdriver.Chrome):
        driver.get(self.URL)
        elements = WebDriverWait(driver, self.WAIT_TIME).until(
            ec.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
        return elements[range_]


class ReportingDataReader(Reader):
    SELECTOR = "div.tcellShort:not([id^='last'])"
    RANGE_ = slice(-1)
    URL = lwt.URL_SENSOR_DATA

    def read(self, phase: int, driver: webdriver.Chrome):
        self._logger.debug(f"confirming Phase {phase + 1} is reading data")
        content = super().read(phase, driver)
        reporting = "Fail" if content == lwt.NO_DATA else "Pass"
        super()._emit_signals(phase, reporting)


class FirmwareVersionReader(Reader):
    """Scrapes the sensor's firmware version from the Software Upgrade page."""

    SELECTOR = "div.tcell"
    RANGE_ = slice(2, 13, 2)
    URL = lwt.URL_SOFTWARE_UPGRADE

    def read(self, phase: int, driver: webdriver.Chrome):
        self._logger.debug(f"reading firmware version for Phase {phase + 1}")
        version = super().read(phase, driver)
        super()._emit_signals(phase, version)
