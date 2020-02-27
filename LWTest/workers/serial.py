from time import sleep

from PyQt5.QtCore import QRunnable, QSettings, QObject, pyqtSignal
from selenium import webdriver

import LWTest.LWTConstants as LWT
from LWTest.constants.dom import serial_number_elements, configuration_frequency, voltage_ride_through, \
    configuration_password, configuration_save_changes
from LWTest.utilities import misc


class Signals(QObject):
    finished = pyqtSignal()
    failed = pyqtSignal()


class SerialConfigWorker(QRunnable):
    def __init__(self, serial_numbers, password, browser, url):
        super().__init__()
        self.settings = QSettings

        self.serial_numbers = misc.ensure_six_numbers(serial_numbers)
        self.password = password
        self.browser = browser
        self.url = url
        self.signals = Signals()

    def run(self):
        self.browser.get(self.url)

        if misc.page_failed_to_load(self.browser, '//*[@id="maindiv"]/form/div[1]/h1[1]'):
            self.signals.failed.emit()
            misc.load_start_page(self.browser)
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

        sleep(1)
        self.signals.finished.emit()


def configure_serial_numbers(serial_numbers: tuple, browser: webdriver.Chrome):
    settings = QSettings()

    worker = SerialConfigWorker(serial_numbers, settings.value("main/config_password"),
                                browser, LWT.URL_CONFIGURATION)

    return worker
