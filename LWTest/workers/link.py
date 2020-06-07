import re
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

        # zero or more whitespace \s* followed by 7 digits \d{7}
        self._serial_number_pattern = re.compile(r"\s*\d{7}")

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

    def _emit_not_linked_signal_for_these_serial_numbers(self, serial_numbers):
        self.signals.link_timeout.emit(tuple(serial_numbers))
        print("timed out waiting for sensors to link")

    def _handle_timeout(self):
        self._emit_not_linked_signal_for_these_serial_numbers(self.serial_numbers)

    def _page_loaded_successfully(self, status_code):
        return status_code == 200

    def _page_not_found(self, status_code):
        return status_code == 404

    def _wait_time_expired(self):
        return self.elapsed_time >= self.timeout

    def _emit_signal_if_linked(self, data):
        if data[0] in self.serial_numbers and len(data) > 3:
            self.signals.successful_link.emit((data[0], data[3]))  # serial number, rssi
            self.serial_numbers.pop(0)

    def _process_line(self, line):
        data = [datum.strip() for datum in line.split(" ") if datum]
        self._emit_signal_if_linked(data)

    def _line_starts_with_serial_number(self, line: str):
        return self._serial_number_pattern.match(line)

    def _process_lines_starting_with_serial_number(self, line):
        if self._line_starts_with_serial_number(line):
            self._process_line(line)

    def _process_page(self, page_text):
        for line in page_text.split("\n"):
            self._process_lines_starting_with_serial_number(line)
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
                self._process_page(page.text)

            sleep(self.time_to_sleep)
            self.elapsed_time += self.time_to_sleep

        self._handle_timeout()
