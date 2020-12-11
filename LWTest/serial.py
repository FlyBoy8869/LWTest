from time import sleep

from selenium import webdriver

import LWTest.constants.dom as dom
from LWTest.web.interface.page import Page

PAGE_LOAD_CONFIRMATION_TEXT: str = "Sensor Configuration"


class ConfigureSerialNumbers:
    def __init__(self, serial_numbers, password, browser, url):
        self._serial_numbers = serial_numbers
        self._password = password
        self._browser: webdriver.Chrome = browser
        self._url = url

    def configure(self):
        if (result := Page.get(self._url, self._browser)) == Page.SUCCESS:
            self._setup_collector()
            return True, ""

        network_msg = "<h3>Network Error configuring collector</h3>" + \
                      "Ensure all connections are made and the collector is powered on."

        server_msg = "<h3>Server Error configuring collector</h3>" + \
                     f"The requested page,<br/><br/>'{self._url}'<br/><br/>was not received.<br/><br/>" + \
                     "There may be an issue with the webserver on the collector."
        return False, network_msg if result == Page.NETWORK_ERROR else server_msg

    def _setup_collector(self):
        self._send_serial_numbers_to_collector()
        self._select_60_hertz()
        self._disable_use_of_voltage_ride_through()
        self._submit_configuration()
        sleep(1)

    def _disable_use_of_voltage_ride_through(self):
        vrt = self._browser.find_element_by_xpath(dom.voltage_ride_through)
        if vrt.is_selected():
            vrt.click()

    def _select_60_hertz(self):
        self._browser.find_element_by_xpath(dom.configuration_frequency).click()

    def _send_serial_numbers_to_collector(self):
        for index, element in enumerate(dom.serial_number_elements):
            field = self._browser.find_element_by_xpath(element)
            field.clear()
            field.send_keys(self._serial_numbers[index])

    def _submit_configuration(self):
        self._browser.find_element_by_xpath(dom.configuration_password).send_keys(self._password)
        self._browser.find_element_by_xpath(dom.configuration_save_changes).click()
