# Note: refactored 06/17/2020
from PyQt5.QtCore import QObject, pyqtSignal
from selenium import webdriver
from time import sleep

import LWTest.constants.dom as dom


class Signals(QObject):
    finished = pyqtSignal()
    failed = pyqtSignal()


class ConfigureSerialNumbers:
    def __init__(self, serial_numbers, password, browser, url):
        self.signals = Signals()
        self._serial_numbers = serial_numbers
        self._password = password
        self._browser: webdriver.Chrome = browser
        self._url = url

    def configure(self):
        if self._page_successfully_loaded():
            self._setup_collector()
            self.signals.finished.emit()
            return

        self.signals.failed.emit()

    def _page_successfully_loaded(self):
        return "Sensor Configuration" in self._get_page_source()

    def _get_page_source(self):
        return self._get_page().page_source

    def _get_page(self):
        self._browser.get(self._url)
        return self._browser

    def _setup_collector(self):
        self._send_serial_numbers_to_collector()
        self._select_60_hertz()
        self._disable_use_of_voltage_ride_through()
        self._confirm_configuration()
        sleep(1)

    def _send_serial_numbers_to_collector(self):
        for index, element in enumerate(dom.serial_number_elements):
            field = self._browser.find_element_by_xpath(element)
            field.clear()
            field.send_keys(self._serial_numbers[index])

    def _select_60_hertz(self):
        self._browser.find_element_by_xpath(dom.configuration_frequency).click()

    def _disable_use_of_voltage_ride_through(self):
        vrt = self._browser.find_element_by_xpath(dom.voltage_ride_through)
        if vrt.is_selected():
            vrt.click()

    def _confirm_configuration(self):
        self._browser.find_element_by_xpath(dom.configuration_password).send_keys(self._password)
        self._browser.find_element_by_xpath(dom.configuration_save_changes).click()
