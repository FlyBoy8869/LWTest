import sys
import traceback
from itertools import dropwhile
from time import sleep

import requests
from PyQt5.QtCore import QRunnable

from LWTest.signals import WorkerSignals

# ------------------------
# ----- For Testing -----
_TESTING = False

doc = ""
file_name = r"tests/webpages/software upgrade example of unit following a failure.html"


def build_document():
    global doc
    with open(file_name, 'r') as in_f:
        for line in in_f:
            doc += line
            yield


genny = build_document()


class Page:
    def __init__(self):
        self.text = None
        self.status_code = 200
# ----- End Test Section -----
# -----------------------------


class UpgradeWorker(QRunnable):
    def __init__(self, serial_number: str, activity_loc: tuple, url: str, ignore_failures: bool = False):
        super().__init__()
        self.serial_number = serial_number
        self.activity_loc = activity_loc
        self.url = url
        self.ignore_failures = ignore_failures
        self.signals = WorkerSignals()

        self.line_count = 0
        self.elapsed_time = 0
        self.timeout = 15
        self.time_to_sleep = 1

    def run(self):
        sleep(5.0)

        # ----- For Testing -----
        global genny
        page = Page()
        # ----- End Test Section -----
        while True:
            try:
                # ----- For Testing -----
                if _TESTING:
                    page.text = doc
                # ----- End Test Section -----
                else:
                    page = requests.get(self.url, timeout=5)
                    html = [line for line in page.text.split("\n")]
                    html.reverse()
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

            if page.status_code == 200:
                self.signals.upgrade_show_activity.emit(self.activity_loc[0])

                for line in html:

                    # Only evaluate the current upgrade session
                    # ignore anything else in the file
                    if self.serial_number in line:
                        break

                    if "Failed to enter program mode" in line:
                        self.signals.upgrade_failed_to_enter_program_mode.emit(self.activity_loc[0])
                        print("Failed to enter program mode.")
                        next(genny)
                        return

                    if "Program Checksum is 0x3d07" in line:
                        self.signals.upgrade_successful.emit(self.serial_number)
                        print(f"Closed found: {line}")
                        print("Sensor firmware successfully upgraded.")
                        return

                if _TESTING:
                    next(genny)

            sleep(1)
