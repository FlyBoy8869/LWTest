import logging
from time import sleep

from PyQt5.QtCore import QRunnable, QObject, pyqtSignal

from LWTest.constants import lwt

if lwt.TESTING_MODE:
    import tests.mock.requests.requests as requests
else:
    import requests

_trigger_words = ['updating', 'entering', 'erasing', 'beginning', 'seg#', 'transfer', 'last']


class UpgradeWorker(QRunnable):
    class Signals(QObject):
        exception = pyqtSignal(str)
        upgrade_failed_to_enter_program_mode = pyqtSignal()
        upgrade_progress = pyqtSignal(int)
        upgrade_successful = pyqtSignal(str)

    def __init__(self, serial_number: str, url: str):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self.signals = self.Signals()
        self.serial_number = serial_number
        self.url = url

    def run(self):
        sleep(lwt.TimeOut.WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE.value)

        line_count = 0
        previous_line_count = 0

        while True:
            try:
                page = requests.get(self.url, timeout=lwt.TimeOut.URL_REQUEST.value)
                if page.status_code != 200:
                    self.signals.exception.emit("Error loading page.")
                    return
                html = page.text.split('\n')

                # work from the bottom of the log file up so that we are only working
                # with the current upgrade session data
                html.reverse()
            except requests.exceptions.ConnectTimeout as exc:
                self._logger.exception("ConnectionTimeout while performing firmware upgrade.", exc_info=exc)
                self.signals.exception.emit("Connection timed out.")
                return
            except requests.exceptions.ConnectionError as exc:
                self._logger.exception("ConnectionError while performing firmware upgrade.", exc_info=exc)
                self.signals.exception.emit("Connection error.")
                return

            for line in html:
                line_count += self._update_line_count(line)

                # Only evaluate the current upgrade session
                # ignore everything else in the file
                if self.serial_number in line:
                    break

                if lwt.UPGRADE_FAILURE_TEXT in line:
                    self.signals.upgrade_failed_to_enter_program_mode.emit()
                    return

                if lwt.UPGRADE_SUCCESS_TEXT in line:
                    self.signals.upgrade_progress.emit(-1)
                    self.signals.upgrade_successful.emit(self.serial_number)
                    return

            lines_read_count = line_count - previous_line_count
            if line_count > previous_line_count:
                previous_line_count += lines_read_count

            self.signals.upgrade_progress.emit(lines_read_count)

            line_count = 0

            sleep(lwt.TimeOut.UPGRADE_LOG_LOAD_INTERVAL.value)

    @staticmethod
    def _update_line_count(line):
        for _trigger_word in _trigger_words:
            if _trigger_word in line.lower():
                return 1
        return 0
