import sys
import traceback
from time import sleep

import requests
from PyQt5.QtCore import QRunnable

import LWTest.LWTConstants as LWT
from LWTest.signals import WorkerSignals
from LWTest.utilities.misc import indicator


class LinkWorker(QRunnable):
    def __init__(self, serial_numbers: tuple, url):
        super().__init__()
        self.serial_numbers = list(serial_numbers)
        self.url = url
        self.signals = WorkerSignals()

        self.time_to_sleep = LWT.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
        self.elapsed_time = 0
        self.timeout = LWT.TimeOut.LINK_CHECK.value

        self.link_indicator = indicator()

    def _show_activity(self, serial_numbers):
        self.signals.link_activity.emit(tuple(serial_numbers), next(self.link_indicator))

    def _notify_page_not_found(self):
        message = ("Received error 404 Page not found.\n" +
                   "Ensure the modem status pages is specified " +
                   "properly in the configuration file.")

        self.signals.url_read_exception.emit((None, None, message))

    def _timed_out_waiting_for_sensors_to_link(self, serial_numbers):
        self.signals.link_timeout.emit(tuple(serial_numbers))
        print("timed out waiting for sensors to link")

    def _page_loaded_successfully(self, status_code):
        return status_code == 200

    def _page_not_found(self, status_code):
        return status_code == 404

    def _wait_time_expired(self):
        return self.elapsed_time >= self.timeout

    def _check_for_link(self, page_text):
        for line in page_text.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                for _ in range(len(self.serial_numbers)):
                    if (serial_number := self.serial_numbers.pop(0)) in line:
                        data = [datum.strip() for datum in line.split(" ") if datum]
                        if len(data) > 3:
                            self.signals.successful_link.emit((data[0], data[3]))  # serial number, rssi
                        else:
                            self.serial_numbers.append(serial_number)
                    else:
                        self.serial_numbers.append(serial_number)

            self._show_activity(self.serial_numbers)

    def _get_page(self):
        try:
            page = requests.get(self.url, timeout=5)
        except requests.exceptions.ConnectTimeout:
            print(traceback.format_exc())
            exc_type, value = sys.exc_info()[:2]
            self.signals.url_read_exception.emit((exc_type, "Connection timed out.", value))
            page = None
        except requests.exceptions.ConnectionError:
            print(traceback.format_exc())
            exc_type, value = sys.exc_info()[:2]
            self.signals.url_read_exception.emit((exc_type, "Connection error", value))
            page = None

        return page

    def run(self):
        while not self._wait_time_expired():
            page = self._get_page()

            if page is None or self._page_not_found(page.status_code):
                self._notify_page_not_found()
                return

            if self._page_loaded_successfully(page.status_code):
                self._check_for_link(page.text)

            sleep(self.time_to_sleep)
            self.elapsed_time += self.time_to_sleep

        self._timed_out_waiting_for_sensors_to_link(self.serial_numbers)
