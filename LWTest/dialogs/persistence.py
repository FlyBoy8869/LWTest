from time import sleep

import requests
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, QRunnable
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

from LWTest.constants import lwt_constants


class PersistenceBootMonitorDialog(QDialog):

    def __init__(self, parent, thread_pool):
        super().__init__(parent=parent)
        self.setWindowTitle("Persistence")

        self.parent = parent
        self._thread_pool = thread_pool
        self.timeout = lwt_constants.TimeOut.COLLECTOR_BOOT_WAIT_TIME.value

        self._need_to_start_thread: bool = True
        self.main_layout = QVBoxLayout()

        self.description_label = QLabel("Waiting for the collector to boot.\t\t")

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar {min-height: 10px; max-height: 10px}")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setTextVisible(False)

        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.progress_bar)

        self.setLayout(self.main_layout)

        QTimer.singleShot(1000, self._wait_for_collector_to_boot)

    def _wait_for_collector_to_boot(self):
        monitor = PageReachable(lwt_constants.URL_RAW_CONFIGURATION, self.timeout)
        monitor.signals.collector_booted.connect(self.accept)
        monitor.signals.dialog_timed_out.connect(self.reject)
        self._thread_pool.start(monitor)


class Signals(QObject):
    collector_booted = pyqtSignal()
    dialog_timed_out = pyqtSignal()


class PageReachable(QRunnable):
    def __init__(self, url: str, timeout: int):
        super().__init__()
        self._url: str = url
        self._timeout: int = timeout
        self.signals = Signals()

    def run(self):
        while self._timeout > 0:
            print(f"timeout = {self._timeout}")
            try:
                if 200 == requests.get(self._url, timeout=lwt_constants.TimeOut.URL_REQUEST.value).status_code:
                    self.signals.collector_booted.emit()
                    sleep(1)
                    return
            except requests.exceptions.RequestException:
                print("unable to load raw config page")

            sleep(1)
            self._timeout -= 1

        self.signals.dialog_timed_out.emit()
