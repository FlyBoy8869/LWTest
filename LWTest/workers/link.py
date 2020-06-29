import datetime
import re
import time

import requests
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
from time import sleep

import LWTest.LWTConstants as LWT
from LWTest.utilities.misc import indicator

linked_regex = r"\s*\d{7}\s*\d{7}\s*\d{7}\s*-?\d{2}"


class Signals(QObject):
    successful_link = pyqtSignal(tuple)
    link_timeout = pyqtSignal(tuple)  # emits the serial numbers that did not link to the collector
    finished = pyqtSignal()


class ModemStatusPageLoader:
    def __init__(self, url: str):
        self._url = url

    @property
    def page(self):
        return self._get_page()

    def _get_page(self):
        try:
            page = requests.get(self._url, timeout=5)
            if page.status_code != 200:
                page = None
        except requests.exceptions.ConnectTimeout:
            page = None
        except requests.exceptions.ConnectionError:
            page = None

        return page


class LinkWorker(QRunnable):
    def __init__(self, serial_numbers: tuple, url):
        super().__init__()
        self.serial_numbers = list(serial_numbers)
        self.url = url
        self.signals = Signals()

        self._page_loader = ModemStatusPageLoader(self.url)

        # zero or more whitespace \s* followed by 7 digits \d{7}
        self._serial_number_pattern = re.compile(r"\s*\d{7}")

        self.time_to_sleep = LWT.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
        self._seconds_elapsed = None
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
        self.signals.finished.emit()

    def _page_loaded_successfully(self, status_code):
        return status_code == 200

    def _page_not_found(self, status_code):
        return status_code == 404

    def _elapsed_seconds_generator(self):
        start_time = datetime.datetime.now()
        while True:
            yield (datetime.datetime.now() - start_time).seconds

    def _timed_out(self):
        return next(self._seconds_elapsed) >= self.timeout

    def _emit_signal_if_linked(self, data):
        print(f"{time.time()} found a link for sensor {data[0]} with an rssi of {data[3]}")
        self.signals.successful_link.emit((data[0], data[3]))  # serial number, rssi

    def _line_starts_with_serial_number(self, line: str):
        return self._serial_number_pattern.match(line)

    def _extract_sensor_record_from_page(self, text):
        sensors = [line.split() for line in text.split('\n') if self._line_starts_with_serial_number(line)]
        return [sensor for sensor in sensors if sensor[0] in self.serial_numbers]

    def _all_sensors_linked(self):
        return len(self.serial_numbers) == 0

    def _process_sensor_records(self, records):
        for record in records:
            if len(record) > 3:
                self._emit_signal_if_linked(record)
                self.serial_numbers.remove(record[0])

    def run(self):
        self._seconds_elapsed = self._elapsed_seconds_generator()

        while not self._timed_out():

            if (page := self._page_loader.page) is None or self._page_not_found(page.status_code):
                self._notify_page_not_found()
                return

            if self._page_loaded_successfully(page.status_code):
                self._process_sensor_records(self._extract_sensor_record_from_page(page.text))
                if self._all_sensors_linked():
                    self.signals.finished.emit()
                    return

            sleep(self.time_to_sleep)
        else:
            self._handle_timeout()
