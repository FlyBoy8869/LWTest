from PyQt5.QtCore import QRunnable
from selenium import webdriver

from LWTest.config.dom import constants
from LWTest.signals import FirmwareSignals


_firmware_version_col = 2


class FirmwareWorker(QRunnable):
    def __init__(self, url: str, browser: webdriver.Chrome, count):
        super().__init__()
        self.url = url
        self.browser = browser
        self.count = count
        self.signals = FirmwareSignals()

    def run(self):
        self.browser.get(self.url)

        for index, element in enumerate(constants.firmware_version[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")

            self.signals.firmware_version.emit((index, _firmware_version_col), content)
