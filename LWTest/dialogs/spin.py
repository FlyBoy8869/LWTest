import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar


class SpinDialog(QDialog):
    def __init__(self, parent, message: str, timeout: int):
        super().__init__(parent=parent)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(QLabel(message))

        self.activity = QProgressBar()
        self.activity.setAlignment(Qt.AlignHCenter)
        self.activity.setMinimum(0)
        self.activity.setMaximum(0)
        self.activity.setTextVisible(False)
        self.main_layout.addWidget(self.activity)

        self.setLayout(self.main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._timer_timeout)
        if timeout:
            QTimer.singleShot(500, lambda: self.timer.start(500))
            self.end_time = time.time() + timeout

    def _timer_timeout(self):
        if time.time() >= self.end_time:
            self.timer.stop()
            self.accept()

        self.raise_()
