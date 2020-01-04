from time import sleep

from PyQt5.QtCore import QRunnable
from selenium import webdriver

from LWTest.collector.readings import FirmwareVersionReader, ReportingDataReader


class PostLinkCheckWorker(QRunnable):
    def __init__(self, parent, index: int, urls: tuple, browser: webdriver.Chrome):
        super().__init__()

        self.parent = parent
        self.index = index
        self.urls = urls
        self.browser = browser

        self.firmware_check = FirmwareVersionReader(self.urls[0], self.browser, self.index)
        self.firmware_check.signals.firmware_version.connect(self.parent._update_firmware_version_column)
        self.firmware_check.signals.firmware_version.connect(
            lambda i, version: self.parent._record_firmware_version(
                self.parent.sensor_log.get_sensor_by_line_position(i[0]).serial_number,
                version))

        self.reporting_check = ReportingDataReader(self.index, self.urls[1], self.browser)
        self.reporting_check.signals.data_reporting_data.connect(
            lambda i, r: self.parent._update_reporting_data_column((i, 3), r))
        self.reporting_check.signals.data_reporting_data.connect(self.parent._record_reporting_data)

    def run(self):
        self.firmware_check.read()
        # sleep(1)
        self.reporting_check.read()

