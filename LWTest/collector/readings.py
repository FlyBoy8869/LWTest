from time import sleep

from PyQt5.QtWidgets import QTableWidget
from selenium import webdriver

from LWTest.config.dom import constants as dom
from LWTest.signals import CollectorSignals, FirmwareSignals
from LWTest.utilities.utilities import get_page_login_if_needed

high_data = (4, 5, 6, 7)
low_data = (8, 9, 10, 11)
temp = 12
fault_current = 13
software_version_col = 2
scale_current = 14
scale_voltage = 15
correction_angle = 16


class Data:
    def __init__(self, url_1: str, url_2: str, browser: webdriver.Chrome, count: int = 6):
        self.url_1 = url_1
        self.url_2 = url_2
        self.browser = browser
        self.count = count
        self.signals = CollectorSignals()

    def read_data(self, voltage_level):
        self.browser.get(self.url_1)

        if voltage_level == "13800":
            data = high_data
        else:
            data = low_data

        for index, element in enumerate(dom.phase_voltage[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")
            self.signals.data_reading.emit((index, data[0]), content)

        for index, element in enumerate(dom.phase_current[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")
            self.signals.data_reading.emit((index, data[1]), content)

        for index, element in enumerate(dom.phase_power_factor[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")
            self.signals.data_reading.emit((index, data[2]), content)

        for index, element in enumerate(dom.phase_real_power[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")
            content = str(int(float(content.replace(",", "")) * 1000))
            self.signals.data_reading.emit((index, data[3]), content)

        for index, element in enumerate(dom.phase_temperature[:self.count]):
            field = self.browser.find_element_by_xpath(element)
            content = field.get_attribute("textContent")
            self.signals.data_reading.emit((index, temp), content)

        if voltage_level == "7200":
            get_page_login_if_needed(self.url_2, self.browser)
            for index, element in enumerate(dom.scale_current[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("value")
                self.signals.data_reading.emit((index, scale_current), content)

            for index, element in enumerate(dom.scale_voltage[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("value")
                self.signals.data_reading.emit((index, scale_voltage), content)

            for index, element in enumerate(dom.raw_configuration_angle[:self.count]):
                field = self.browser.find_element_by_xpath(element)
                content = field.get_attribute("value")
                self.signals.data_reading.emit((index, correction_angle), content)


class FaultCurrent:
    def __init__(self, url: str, browser: webdriver.Chrome):
        self.url = url
        self.browser = browser
        self.signals = CollectorSignals()

    def read_fault_current(self):
        self.browser.get(self.url)
        sleep(1)
        field = self.browser.find_element_by_xpath(dom.fault_current_1)
        if int(field.get_attribute("textContent")) >= 0:
            self.signals.fault_current.emit("Pass")
        else:
            self.signals.fault_current.emit("Fail")


class Persistence:
    def __init__(self):
        self.signals = CollectorSignals()

    def check_persistence(self, url: str, browser: webdriver.Chrome, table: QTableWidget, count: int = 6):
        get_page_login_if_needed(url, browser)

        scale_currents = []
        scale_voltages = []
        correction_angles = []

        for element in dom.scale_current[:count]:
            field = browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            scale_currents.append(value)

        for element in dom.scale_voltage[:count]:
            field = browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            scale_voltages.append(value)

        for element in dom.raw_configuration_angle[:count]:
            field = browser.find_element_by_xpath(element)
            value = field.get_attribute("value")
            correction_angles.append(value)

        for index in range(count):
            if scale_currents[index] == table.item(index, 14).text():
                self.signals.data_persisted.emit("Yes", index, 17)
            else:
                self.signals.data_persisted.emit("Fail", index, 17)

        for index in range(count):
            if scale_voltages[index] == table.item(index, 15).text():
                self.signals.data_persisted.emit("Yes", index, 17)
            else:
                self.signals.data_persisted.emit("Fail", index, 17)

        for index in range(count):
            if correction_angles[index] == table.item(index, 16).text():
                self.signals.data_persisted.emit("Yes", index, 17)
            else:
                self.signals.data_persisted.emit("Fail", index, 17)
