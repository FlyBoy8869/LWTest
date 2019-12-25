from PyQt5.QtCore import QRunnable, QSettings

from LWTest.config.dom.constants import serial_number_elements, configuration_frequency, voltage_ride_through, \
    configuration_password, configuration_save_changes
from LWTest.signals import WorkerSignals
from LWTest.utilities import utilities


class SerialConfigWorker(QRunnable):
    def __init__(self, serial_numbers, password, browser, url):
        super().__init__()
        self.settings = QSettings

        self.serial_numbers = serial_numbers
        self.password = password
        self.browser = browser
        self.url = url
        self.signals = WorkerSignals()

    def run(self):
        self.browser.get(self.url)

        if utilities.page_failed_to_load(self.browser, '//*[@id="maindiv"]/form/div[1]/h1[1]'):
            self.signals.serial_config_page_failed_to_load.emit(self.url, self.serial_numbers)
            utilities.load_start_page(self.browser)
            return

        for index, element in enumerate(serial_number_elements):
            field = self.browser.find_element_by_xpath(element)
            field.clear()
            field.send_keys(self.serial_numbers[index])

        # select 60Hz
        self.browser.find_element_by_xpath(configuration_frequency).click()

        # don't use voltage ride through
        vrt = self.browser.find_element_by_xpath(voltage_ride_through)
        if vrt.is_selected():
            vrt.click()

        self.browser.find_element_by_xpath(configuration_password).send_keys(self.password)

        self.browser.find_element_by_xpath(configuration_save_changes).click()

        self.signals.configured_serial_numbers.emit(tuple(self.serial_numbers))
