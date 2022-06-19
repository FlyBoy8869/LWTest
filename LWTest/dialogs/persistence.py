import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

from LWTest.collector.state.reachable import PageReachable
from LWTest.constants import lwt_constants


class PersistenceBootMonitorDialog(QDialog):
    """Waits three minutes for the collector to boot before automatically closing."""

    def __init__(self, parent, *, timeout=180):
        super().__init__(parent=parent)
        self.setWindowTitle("Persistence")

        self.parent = parent
        self.monitor = PageReachable(lwt_constants.URL_RAW_CONFIGURATION)

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

        self.end_time = time.time() + timeout
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._wait_for_collector_to_boot)
        QTimer.singleShot(1000, lambda: self.timer.start(5000))

    def _wait_for_collector_to_boot(self):
        if self.monitor.try_to_load() or time.time() >= self.end_time:
            self.timer.stop()
            self.accept()
