import logging
import re
import requests
import time
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
from time import sleep

from LWTest.constants import lwt

linked_regex = r"\s*\d{7}\s*\d{7}\s*\d{7}\s*-?\d{2}"


class Signals(QObject):
    successful_link = pyqtSignal(tuple)
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


class LinkWorker(QRunnable):
    def __init__(self, serial_numbers: list, url):
        super().__init__()
        self.signals = Signals()

        self.__logger = logging.getLogger(__name__)
        self.__serial_numbers = serial_numbers
        self.__page_loader = ModemStatusPageLoader(url)

        # zero or more whitespace \s* followed by 7 digits \d{7}
        self.__serial_number_pattern = re.compile(r"\s*\d{7}")

        self.__time_to_sleep = lwt.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
        self.__timeout = lwt.TimeOut.LINK_CHECK.value

    def run(self):
        start_time = time.time()
        try:
            while time.time() - start_time < self.__timeout:
                if (page := self.__page_loader.page) is None or self._page_not_found(page.status_code):
                    self._notify_page_not_found()
                    return

                if page.status_code == 200:
                    self._process_sensor_records(self._extract_sensor_record_from_page(page.text))
                    if self._all_sensors_linked():
                        self.signals.finished.emit()
                        return

                sleep(self.__time_to_sleep)

            self._handle_timeout()
        except requests.exceptions.RequestException as exc:
            self.__logger.exception("Error checking link status", exc_info=exc)
        finally:
            self.signals.finished.emit()

    def _all_sensors_linked(self):
        return len(self.__serial_numbers) == 0

    def _emit_not_linked_signal_for_these_serial_numbers(self, serial_numbers):
        self.signals.link_timeout.emit(tuple(serial_numbers))
        print("timed out waiting for sensors to link")

    def _emit_signal_if_linked(self, data):
        print(f"{time.time()} found a link for sensor {data[0]} with an rssi of {data[3]}")
        self.signals.successful_link.emit((data[0], data[3]))  # serial number, rssi

    def _extract_sensor_record_from_page(self, text):
        sensors = [line.split() for line in text.split('\n') if self._line_starts_with_serial_number(line)]
        return [sensor for sensor in sensors if sensor[0] in self.__serial_numbers]

    def _handle_timeout(self):
        self._emit_not_linked_signal_for_these_serial_numbers(self.__serial_numbers)
        self.signals.finished.emit()

    def _line_starts_with_serial_number(self, line: str):
        return self.__serial_number_pattern.match(line)

    def _notify_page_not_found(self):
        message = ("Received error 404 Page not found.\n" +
                   "Ensure the modem status pages is specified " +
                   "properly in the configuration file.")

        self.signals.url_read_exception.emit((None, None, message))

    def _process_sensor_records(self, records):
        for record in records:
            if len(record) > 3:
                self._emit_signal_if_linked(record)
                self.__serial_numbers.remove(record[0])

    @staticmethod
    def _page_not_found(status_code):
        return status_code == 404
