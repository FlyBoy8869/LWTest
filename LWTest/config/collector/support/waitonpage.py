# waitonpage.py

import requests
from PyQt5.QtCore import QSettings, Qt, QTimer, QEvent
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QDialogButtonBox, QHBoxLayout
from typing import List


class WaitForTextOnPage(QDialog):
    """Wait until specific text is present on a page."""

    ACCEPTED = QDialog.Accepted
    REJECTED = QDialog.Rejected
    WAIT_TIME_EXPIRED = 3

    def __init__(self, parent, url, text, wait_time=150, monitor=False):
        """
        Parameters
        ----------
        parent
            The parent of this dialog window.

        url: str
            The url of the page to check for 'text'.

        text: str
            The text to search for on the page.

        wait_time: int
            The time to wait for the text to be present.

            default = 150 seconds

        Returns
        -------
            QDialog.Accepted if the text is found.
            QDialog.Rejected if dialog is cancelled.
            WaitForTextOnPage.WAIT_TIME_EXPIRED if 'wait_time' has elapsed.
        """
        super().__init__(parent)
        settings = QSettings()

        self.url = url
        self.text = text
        self.wait_time = wait_time
        self.monitor = monitor
        self.is_running = False
        self.request_timeout = int(settings.value("main/request_timeout"))
        self.check_interval = 10
        self.check_interval_remaining = self.check_interval

        self.setWindowTitle("Low Amperage Boot")

        self.main_layout = QVBoxLayout()
        self.serial_label_layout = QHBoxLayout()
        self.message_label_layout = QHBoxLayout()

        self.lbl_hourglass = QLabel()
        self.movie_hourglass = QMovie(r"laboot\resources\images\animations\activity_green_fast.gif")
        self.lbl_hourglass.setMovie(self.movie_hourglass)
        self.lbl_hourglass.setAlignment(Qt.AlignHCenter)

        self.lbl_serial_detect = QLabel(f"Serial number {self.text} was not detected.")
        font = self.lbl_serial_detect.font()
        font.setPointSize(10)
        self.lbl_serial_detect.setFont(font)
        self.lbl_serial_detect.setAlignment(Qt.AlignHCenter)

        text = ("Monitoring collector for refresh of serial numbers." if monitor
                else "Waiting for collector to refresh serial numbers.")
        self.lbl_main_message = QLabel(text)
        self.lbl_main_message.setFont(font)
        self.lbl_main_message.setAlignment(Qt.AlignHCenter)

        self.lbl_separator = QLabel("_" * 50)
        self.lbl_separator.setAlignment(Qt.AlignHCenter)

        # self.pb_counter = QProgressBar(self)
        # self.pb_counter.installEventFilter(self)
        # self.pb_counter.setTextVisible(False)
        # self.pb_counter.setRange(0, self.wait_time)
        # self.pb_counter.setMinimum(0)
        # self.pb_counter.setMaximum(self.wait_time)
        # self.pb_counter.setValue(self.wait_time)

        btns = QDialogButtonBox()
        btns.setStandardButtons(QDialogButtonBox.Cancel)
        btns.rejected.connect(lambda: self.done(WaitForTextOnPage.REJECTED))

        self.main_layout.addWidget(self.lbl_hourglass, Qt.AlignHCenter)

        self.serial_label_layout.addWidget(self.lbl_serial_detect, Qt.AlignCenter)
        self.main_layout.addLayout(self.serial_label_layout, stretch=1)

        self.message_label_layout.addWidget(self.lbl_main_message, Qt.AlignCenter)
        self.main_layout.addLayout(self.message_label_layout, stretch=1)

        self.main_layout.addWidget(self.lbl_separator, Qt.AlignCenter)

        # self.frame_layout.addWidget(self.pb_counter, Qt.AlignCenter)
        self.main_layout.addWidget(btns)

        # self.count_down_timer = QTimer(self)
        # self.count_down_timer.timeout.connect(lambda: self.pb_counter.setValue(self.pb_counter.value() - 1))

        self.check_page_timer = QTimer(self)
        self.check_page_timer.timeout.connect(self._check_page)

        self.setLayout(self.main_layout)

    def start(self):
        self.open()
        self.is_running = True
        self.movie_hourglass.start()
        # self.count_down_timer.start(1000)
        self.check_page_timer.start(self.check_interval * 1000)

        # time to spend waiting for the collector to update
        QTimer(self).singleShot(self.wait_time * 1000, self.stop)

    def stop(self):
        # self.count_down_timer.stop()
        self.check_page_timer.stop()
        self.done(WaitForTextOnPage.WAIT_TIME_EXPIRED)

    def _check_page(self):
        # self.wait_time -= 1
        # self.check_interval_remaining -= 1

        # if self.check_interval_remaining <= 0:
        in_source: List[str] = self._get_source_as_list(self.url, self.request_timeout)
        if self._find(self.text, in_source):
            self.done(WaitForTextOnPage.ACCEPTED)

        # self.check_interval_remaining = self.check_interval

    @staticmethod
    def _get_source_as_list(url: str, timeout: int = 1) -> List[str]:
        r = requests.get(url, timeout=timeout)
        return r.text.split("\n")

    @staticmethod
    def _find(text: str, source: List[str]) -> bool:
        for line in source:
            if text in line.strip():
                return True

        return False

    def eventFilter(self, obj, event) -> bool:
        if obj is self.pb_counter:
            if event.type() == QEvent.Resize:
                self.pb_counter.setFixedHeight(10)
                return True
            else:
                return False

        # the I don't care about other widgets response :)
        return QDialog.eventFilter(obj, event)
