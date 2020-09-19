from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar


class SpinDialog(QDialog):
    def __init__(self, parent, message: str, timeout: int):
        super().__init__(parent=parent)
        self.timeout = timeout

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

    def showEvent(self, q_show_event):
        if self.timeout != 0 and not self.timer.isActive():
            self.timer.start(1000)

    def go_away(self):
        self.done(QDialog.Accepted)

    def _timer_timeout(self):
        self.timeout -= 1
        if self.timeout < 1:
            self.timer.stop()
            self.accept()