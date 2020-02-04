import sys
import traceback
from time import sleep

import requests
from PyQt5.QtCore import QRunnable

import LWTest.LWTConstants as LWT
from LWTest.signals import WorkerSignals
from LWTest.utilities.misc import indicator


class LinkWorker(QRunnable):
    def __init__(self, serial_numbers, url):
        super().__init__()
        self.serial_numbers = serial_numbers
        self.url = url
        self.signals = WorkerSignals()

        self.time_to_sleep = LWT.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
        self.elapsed_time = 0
        self.timeout = LWT.TimeOut.LINK_CHECK.value

        self.link_indicator = indicator()

    def run(self):
        serial_numbers: list = list(self.serial_numbers)
        items_to_remove = []
        while True:
            try:
                page = requests.get(self.url, timeout=5)
                print("retrieved page")
            except requests.exceptions.ConnectTimeout:
                print(traceback.format_exc())
                exc_type, value = sys.exc_info()[:2]
                self.signals.url_read_exception.emit((exc_type, "Connection timed out.", value))
                return
            except requests.exceptions.ConnectionError:
                print(traceback.format_exc())
                exc_type, value = sys.exc_info()[:2]
                self.signals.url_read_exception.emit((exc_type, "Connection error", value))
                return

            if page.status_code == 404:
                message = ("Received error 404 Page not found.\n" +
                           "Ensure the modem status pages is specified " +
                           "properly in the configuration file.")

                self.signals.url_read_exception.emit((None, None, message))
                return

            try:
                if page.status_code == 200:
                    self.signals.link_activity.emit(tuple(serial_numbers), next(self.link_indicator))

                    for line in page.text.split("\n"):
                        line = line.strip()
                        if line and line[0].isdigit():
                            for serial_number in serial_numbers:
                                if serial_number in line:
                                    data = [datum.strip() for datum in line.split(" ") if datum]
                                    if len(data) > 3:
                                        self.signals.successful_link.emit((data[0], data[3]))  # serial number, rssi
                                        items_to_remove.append(serial_number)

                            if items_to_remove:
                                for e in items_to_remove:
                                    serial_numbers.remove(e)
                                items_to_remove = []

                            if len(serial_numbers) == 0:
                                return
            except:
                print(traceback.format_exc())
                return

            sleep(self.time_to_sleep)
            self.elapsed_time += self.time_to_sleep
            if self.elapsed_time >= self.timeout:
                self.signals.link_timeout.emit(tuple(serial_numbers))
                self.signals.resize_columns.emit()
                return
