import logging
import time
from typing import List

from PyQt6 import QtGui
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from LWTest.collector.common.constants import ReadingType
from LWTest.constants import lwt_constants
from LWTest.sensor import SensorLog
from LWTest.workers.link import LinkChecker

_logger = logging.getLogger(__name__)
_quit_checking = False


class Worker(QObject):
    update = pyqtSignal(str, int, str)
    finished = pyqtSignal()

    def __init__(self):
        super(Worker, self).__init__()

    def do_work(self, serial_number: str, checker: LinkChecker):
        _logger.info(f"checking sensor {serial_number} link status")
        value = rssi if (rssi := checker.check(serial_number)) else "NA"
        # noinspection PyUnresolvedReferences
        self.update.emit(value, ReadingType.RSSI, serial_number)


class Signals(QObject):
    update = pyqtSignal(str, int, str)
    finished = pyqtSignal()


class RSSIDialog(QDialog):
    """Waits three minutes for the collector to boot before automatically closing."""
    TIMEOUT = lwt_constants.TimeOut.LINK_CHECK.value

    def __init__(self, parent, sensor_log: SensorLog):
        super().__init__(parent=parent)
        self.setWindowTitle("RSSI")

        self._parent = parent
        self.signals = Signals()
        self._sensor_log = sensor_log
        self._threads: List[QThread] = []
        self._timeout = time.time() + lwt_constants.TimeOut.LINK_CHECK.value

        self.main_layout = QVBoxLayout()

        self.description_label = QLabel("Collecting RSSI values.\t\t")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar {min-height: 10px; max-height: 10px}")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setTextVisible(False)

        self._cancel_button = QPushButton("cancel")
        # noinspection PyUnresolvedReferences
        self._cancel_button.clicked.connect(self._close)

        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self._cancel_button)

        self.setLayout(self.main_layout)

        self.timer = QTimer()
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self._check_link_status)
        self.timer.start(1000)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        for thread in self._threads:
            try:
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
            except RuntimeError:
                continue

        a0.accept()

    def _close(self):
        self.close()

    def _create_thread(self, serial_number: str):
        thread = QThread()
        worker = Worker()
        worker.moveToThread(thread)
        # noinspection PyUnresolvedReferences
        thread.started.connect(
            lambda: worker.do_work(
                serial_number, LinkChecker(lwt_constants.URL_MODEM_STATUS)
            )
        )
        # noinspection PyUnresolvedReferences
        worker.update.connect(self._update)
        # noinspection PyUnresolvedReferences
        worker.finished.connect(thread.quit)
        # noinspection PyUnresolvedReferences
        worker.finished.connect(worker.deleteLater)
        # noinspection PyUnresolvedReferences
        thread.finished.connect(thread.deleteLater)
        return thread

    def _start_threads(self, serial_numbers):
        self._threads.clear()
        self._threads = [self._create_thread(serial_number)
                         for serial_number in serial_numbers]
        for thread in self._threads:
            thread.start()

    def _check_link_status(self):
        if (serial_numbers := self._sensor_log.unlinked) and time.time() < self._timeout:
            if not self._check_for_running_threads():
                self._start_threads(serial_numbers)
        else:
            self.timer.stop()
            # noinspection PyUnresolvedReferences
            self.signals.finished.emit()
            self.close()

    def _check_for_running_threads(self):
        for thread in self._threads:
            try:
                if thread.isRunning():
                    return True
            except RuntimeError:
                continue

        return False

    def _update(self, value: str, reading_type: ReadingType, serial_number: str):
        # noinspection PyUnresolvedReferences
        self.signals.update.emit(value, reading_type, serial_number)
