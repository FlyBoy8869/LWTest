from time import sleep

import requests
from PyQt5.QtCore import QTimer, QRunnable, QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout, QDialogButtonBox


class Signals(QObject):
    collector_booted = pyqtSignal()


class PersistenceWaitDialog(QDialog):
    def __init__(self, parent, title: str, message: str, timeout: int, url: str = None):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.message = message
        self.url = url

        if url:
            self.timeout = 180
        else:
            self.timeout = timeout

        self.parent = parent
        self.thread_started = False
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.description_label = QLabel(self.message)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)

        if url:
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMaximum(self.timeout)

        if not url:
            self.progress_bar.setValue(self.timeout)
        self.progress_bar.setTextVisible(False)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.button_box)

        self.setLayout(self.main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_timeout)

    def showEvent(self, QShowEvent):
        if not self.timer.isActive():
            self.timer.start(1000)

        if self.url:
            if not self.thread_started:
                self._wait_for_collector_to_boot()
                self.thread_started = True

    def timer_timeout(self):
        if self.timeout == 0:
            return
        elif self.timeout > 1:
            self.timeout -= 1
            self.progress_bar.setValue(self.timeout)
        else:
            self._stop_timer()
            self.accept()

    def _wait_for_collector_to_boot(self):
        class Booted(QRunnable):
            def __init__(self, url: str):
                super().__init__()
                self.url = url
                self.signals = Signals()

            def run(self):
                while True:
                    try:
                        print(f"{__name__}._wait_for_collector_to_boot: loading page")
                        page = requests.get(self.url, timeout=2)

                        if page.status_code == 200:
                            print(f"{__name__}._wait_for_collector_to_boot: page successfully loaded")
                            self.signals.collector_booted.emit()
                            return
                    except requests.exceptions.RequestException:
                        print(f"{__name__}._wait_for_collector_to_boot: collector not ready, retrying...")
                        pass

                    sleep(1)

        boot_checker = Booted(self.url)
        # methods are executed inside a tuple to allow multiple statements inside the lambda
        # then the tuple is just thrown away
        boot_checker.signals.collector_booted.connect(lambda: (self._stop_timer(), self.accept()))
        self.parent.thread_pool.start(boot_checker)

    def _stop_timer(self):
        self.timer.stop()
