from time import sleep

import requests
from PyQt5.QtCore import QObject, pyqtSignal

import LWTest.constants.LWTConstants as LWT


class Signals(QObject):
    confirmed = pyqtSignal()
    error = pyqtSignal()
    timeout = pyqtSignal()


class ConfirmSerialConfig:
    def __init__(self, serial_numbers: tuple, url: str):
        self.signals = Signals()

        self.serial_numbers = serial_numbers
        self.url = url
        self.check_interval = LWT.TimeOut.URL_READ_INTERVAL.value
        self.elapsed_time = 0
        self.timeout = LWT.TimeOut.CONFIRM_SERIAL_CONFIG.value

    def read(self):
        while self.elapsed_time < self.timeout:
            try:
                page = requests.get(self.url, timeout=5)

                if page.status_code == 200:
                    for line in page.text.split('\n'):
                        for serial_number in self.serial_numbers:
                            if serial_number in line:
                                self.signals.confirmed.emit()
                                return
            except requests.exceptions.RequestException:
                self.signals.error.emit()

            sleep(self.check_interval)
            self.elapsed_time += self.check_interval

        self.signals.timeout.emit()
