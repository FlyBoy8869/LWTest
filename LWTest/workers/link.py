import logging
import re
from typing import Tuple

import requests
import time
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
from time import sleep

from LWTest.constants import lwt
from LWTest.collector import ReadingType

_serial_number_regex = re.compile(r"\s*\d{7}")
linked_regex = r"\s*\d{7}\s*\d{7}\s*\d{7}\s*-?\d{2}"


class Signals(QObject):
    successful_link = pyqtSignal(str, int, str)
    link_timeout = pyqtSignal(tuple)  # emits the serial numbers that did not link to the collector
    finished = pyqtSignal()
    url_read_exception = pyqtSignal(tuple)


class ModemStatusPageLoader:
    def __init__(self, url: str):
        self.__url = url

    @property
    def page(self):
        return self._get_page()

    def _get_page(self):
        try:
            page = requests.get(self.__url, timeout=20)
            if page.status_code != 200:
                page = None
        except requests.exceptions.ConnectTimeout:
            page = None
        except requests.exceptions.ConnectionError:
            page = None

        return page


class SerialNumberUpdateVerifier(QObject):
    serial_numbers_updated = pyqtSignal()
    timed_out = pyqtSignal()

    def __init__(self, serial_numbers: Tuple[str]):
        super().__init__()
        self._serial_numbers = serial_numbers
        self._page_loader = ModemStatusPageLoader(lwt.URL_MODEM_STATUS)
        self._timeout = 180

    def verify(self):
        end_time = time.time() + self._timeout
        while time.time() < end_time:
            page = self._page_loader.page
            if page.status_code != 200:
                return

            if len(_extract_sensor_record_from_page(page.text, self._serial_numbers)) == len(self._serial_numbers):
                logging.getLogger(__name__).info("serial numbers updated...")
                self.serial_numbers_updated.emit()
                return

            sleep(0.300)

        self.timed_out.emit()


class LinkWorker(QRunnable):
    def __init__(self, serial_numbers: list, url):
        super().__init__()
        self.signals = Signals()

        self._logger = logging.getLogger(__name__)
        self._serial_numbers = serial_numbers
        self._page_loader = ModemStatusPageLoader(url)

        self._time_to_sleep = lwt.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
        self._timeout = lwt.TimeOut.LINK_CHECK.value

    def run(self):
        self._logger.debug("LinkWorker thread run method started")
        start_time = time.time()
        try:
            while time.time() - start_time < self._timeout:
                if (page := self._page_loader.page) is None or self._page_not_found(page.status_code):
                    self._notify_page_not_found()
                    return

                if page.status_code == 200:
                    self._process_sensor_records(_extract_sensor_record_from_page(page.text, self._serial_numbers))
                    if self._all_sensors_linked():
                        return

                sleep(self._time_to_sleep)

            self._handle_timeout()
        except requests.exceptions.RequestException as exc:
            self._logger.exception("Error checking link status", exc_info=exc)
        finally:
            self._logger.debug("emitting 'finished' signal")
            self.signals.finished.emit()

    def _all_sensors_linked(self):
        return len(self._serial_numbers) == 0

    def _emit_not_linked_signal_for_these_serial_numbers(self, serial_numbers):
        self.signals.link_timeout.emit(tuple(serial_numbers))
        self._logger.debug("timed out waiting for sensors to link")

    def _emit_signal_if_linked(self, data):
        self._logger.debug(f"{time.time()} found a link for sensor {data[0]} with an rssi of {data[3]}")
        serial_number, rssi = data[0], data[3]
        self.signals.successful_link.emit(rssi, ReadingType.RSSI, serial_number)

    def _handle_timeout(self):
        self._emit_not_linked_signal_for_these_serial_numbers(self._serial_numbers)

    def _notify_page_not_found(self):
        message = ("Received error 404 Page not found.\n" +
                   "Ensure the modem status pages is specified " +
                   "properly in the configuration file.")

        self.signals.url_read_exception.emit((None, None, message))

    def _process_sensor_records(self, records):
        for record in records:
            if len(record) > 3:
                self._emit_signal_if_linked(record)
                self._serial_numbers.remove(record[0])

    @staticmethod
    def _page_not_found(status_code):
        return status_code == 404


#
# stand-alone functions
def _line_starts_with_serial_number(line: str):
    return _serial_number_regex.match(line)


def _extract_sensor_record_from_page(text, serial_numbers):
    sensor_records = [line.split() for line in text.split('\n') if _line_starts_with_serial_number(line)]
    return [sensor for sensor in sensor_records if sensor[0] in serial_numbers]
