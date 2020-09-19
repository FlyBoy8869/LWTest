from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QDialogButtonBox

from LWTest.utilities import time as util_time


class CountDownDialog(QDialog):
    progress_bar_stylesheet = "QProgressBar {min-height: 10px; max-height: 10px; " + \
                              "margin-top:10px; margin-bottom: 10px}"

    def __init__(self, parent, title: str, message: str, timeout: int):
        super().__init__(parent=parent)
        self.setWindowTitle(title)

        self._main_layout = QVBoxLayout()
        self._button_layout = QHBoxLayout()

        self._description_label = QLabel(message)

        self._timeout = timeout
        self._progress_bar = QProgressBar()
        self._progress_bar.setStyleSheet(self.progress_bar_stylesheet)
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(self._timeout)
        self._progress_bar.setValue(self._timeout)
        self._progress_bar.setTextVisible(False)

        self._remaining_time_label = QLabel("")

        self._button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self._button_box.rejected.connect(self.reject)

        self._main_layout.addWidget(self._description_label)
        self._main_layout.addWidget(self._progress_bar)
        self._main_layout.addWidget(self._remaining_time_label, alignment=Qt.AlignHCenter)
        self._main_layout.addWidget(self._button_box)

        self.setLayout(self._main_layout)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._handle_timeout)

    def showEvent(self, q_show_event):
        if not self._timer.isActive():
            self._remaining_time_label.setText(util_time.format_seconds_to_minutes_and_seconds(self._timeout))
            self._timer.start(1000)

    def _timer_expired(self):
        return self._timeout <= 0

    def _terminate_on_timer_expiration(self):
        if self._timer_expired():
            self._timer.stop()
            self.accept()

    def _update_display(self):
        self._progress_bar.setValue(self._timeout)
        self._remaining_time_label.setText(util_time.format_seconds_to_minutes_and_seconds(self._timeout))

    def _decrement_timer(self):
        self._timeout -= 1

    def _handle_timeout(self):
        self._decrement_timer()
        self._update_display()
        self._terminate_on_timer_expiration()