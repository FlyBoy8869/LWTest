import sys
import traceback
from time import sleep

from PyQt5.QtCore import QRunnable

import LWTest.constants.LWTConstants as LWT
from LWTest.signals import WorkerSignals

if LWT.TESTING_MODE:
    import LWTest.tests.mock.requests.requests as requests
else:
    import requests

_trigger_words = ['updating', 'entering', 'erasing', 'beginning', 'seg#', 'transfer', 'last']


class UpgradeWorker(QRunnable):
    def __init__(self, serial_number: str, url: str):
        super().__init__()
        self.serial_number = serial_number
        self.url = url
        self.signals = WorkerSignals()

    def run(self):
        sleep(LWT.TimeOut.WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE.value)

        line_count = 0
        previous_line_count = 0

        while True:

            try:
                page = requests.get(self.url, timeout=LWT.TimeOut.URL_REQUEST.value)
                html = page.text.split('\n')

                # work from the bottom of the log file up so that we are only working
                # with the current upgrade session data
                html.reverse()

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

            if page.status_code == 200:

                for line in html:

                    for _trigger_word in _trigger_words:
                        if _trigger_word in line.lower():
                            line_count += 1

                    # Only evaluate the current upgrade session
                    # ignore everything else in the file
                    if self.serial_number in line:
                        break

                    if LWT.UPGRADE_FAILURE_TEXT in line:
                        self.signals.upgrade_failed_to_enter_program_mode.emit()
                        return

                    if LWT.UPGRADE_SUCCESS_TEXT in line:
                        self.signals.upgrade_progress.emit(-1)
                        self.signals.upgrade_successful.emit(self.serial_number)
                        return

                lines_read_count = line_count - previous_line_count
                if line_count > previous_line_count:
                    previous_line_count += lines_read_count

                self.signals.upgrade_progress.emit(lines_read_count)

                line_count = 0

            sleep(LWT.TimeOut.UPGRADE_LOG_LOAD_INTERVAL.value)
