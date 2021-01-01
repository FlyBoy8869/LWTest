import logging
import re
import time
from time import sleep
from typing import Tuple

import requests
from PyQt5.QtCore import QObject, pyqtSignal, QMutex

from LWTest.collector.common.constants import ReadingType
from LWTest.constants import lwt

_serial_number_regex = re.compile(r"\s*\d{7}")
linked_regex = r"\s*\d{7}\s*\d{7}\s*\d{7}\s*-?\d{2}"


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


class LinkChecker:
    time_to_sleep = lwt.TimeOut.LINK_PAGE_LOAD_INTERVAL.value
    timeout = lwt.TimeOut.LINK_CHECK.value

    def __init__(self, url: str):
        super().__init__()

        self._logger = logging.getLogger(__name__)
        self._page_loader = ModemStatusPageLoader(url)

    def check(self, serial_number: str):
        page = self._page_loader.page
        number, rssi = self._process_sensor_records(_extract_sensor_record_from_page(page.text, (serial_number,)))
        if number:
            return rssi

        return None

    @staticmethod
    def _process_sensor_records(records):
        for record in records:
            if len(record) > 3:
                return record[0], record[3]

        return None, None


#
# stand-alone functions
def _line_starts_with_serial_number(line: str):
    return _serial_number_regex.match(line)


def _extract_sensor_record_from_page(text, serial_numbers: tuple):
    sensor_records = [line.split() for line in text.split('\n') if _line_starts_with_serial_number(line)]
    return [record for record in sensor_records if record[0] in serial_numbers]
