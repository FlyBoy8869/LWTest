import sys
import traceback
from itertools import dropwhile
from time import sleep

import requests
from PyQt5.QtCore import QRunnable

from LWTest.signals import WorkerSignals


# ------------------------
# ----- For Testing -----
_TESTING = True

doc = ""
file_name = r"C:\Users\charles\Downloads\LineWatch\webpages\software upgrade example of unit following a failure.html"


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
    def __init__(self, serial_number, url, ignore_failures=False):
        super().__init__()
        self.serial_number = serial_number
        self.url = url
        self.ignore_failures = ignore_failures
        self.signals = WorkerSignals()

        self.line_count = 0
        self.elapsed_time = 0
        self.timeout = 15
        self.time_to_sleep = 1

    def run(self):
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
                self.signals.upgrade_show_activity.emit(self.serial_number)

                for line in dropwhile(lambda l: self.serial_number not in l, page.text.split('\n')):

                    self.line_count += 1

                    if "Failed to enter program mode" in line:
                        if self.ignore_failures:
                            continue
                        else:
                            self.signals.upgrade_failed_to_enter_program_mode.emit(self.serial_number)
                            print("Failed to enter program mode.")
                            next(genny)
                            return

                    if "Program Checksum is 0x3d07" in line:
                        self.signals.upgrade_successful.emit(self.serial_number)
                        print(f"Closed found: {line}")
                        print("Sensor firmware successfully upgraded.")
                        return

                print(f"self.line_count = {self.line_count}")

                if _TESTING:
                    next(genny)
