from time import sleep
from typing import Callable

import requests
from PyQt5.QtCore import QTimer, QRunnable, QObject, pyqtSignal, Qt, QSettings
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout, QDialogButtonBox

import LWTest.LWTConstants as LWT
from LWTest.collector.read.confirm import ConfirmSerialConfig
from LWTest.config.dom import constants
from LWTest.workers.confirm import ConfirmSerialConfigWorker
from LWTest.workers.upgrade import UpgradeWorker


class Signals(QObject):
    collector_booted = pyqtSignal()


class UpgradeSignals(QObject):
    cancelled = pyqtSignal()


class PersistenceBootMonitor(QDialog):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Persistence")

        self.parent = parent
        # self.url = LWT.URL_RAW_CONFIGURATION
        self.timeout = LWT.TimeOut.COLLECTOR_BOOT_WAIT_TIME.value

        self.thread_started = False
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.description_label = QLabel("Please, wait for the collector to boot.\t\t")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
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

        if not self.thread_started:
            self._wait_for_collector_to_boot()
            self.thread_started = True

    def timer_timeout(self):
        if self.timeout > 0:
            self.timeout -= 1
        else:
            self._stop_timer()
            self.accept()

    def _wait_for_collector_to_boot(self):
        class PageReachable(QRunnable):
            def __init__(self, url: str):
                super().__init__()
                self.url = url
                self.signals = Signals()

            def run(self):
                while True:
                    try:
                        print(f"{__name__}._wait_for_collector_to_boot: loading page")
                        page = requests.get(self.url, timeout=LWT.TimeOut.URL_REQUEST.value)

                        if page.status_code == 200:
                            print(f"{__name__}._wait_for_collector_to_boot: page successfully loaded")
                            self.signals.collector_booted.emit()
                            return
                    except requests.exceptions.RequestException:
                        print(f"{__name__}._wait_for_collector_to_boot: collector not ready, retrying...")
                        pass

                    sleep(1)

        monitor = PageReachable(LWT.URL_RAW_CONFIGURATION)
        # methods are executed inside a tuple to allow multiple statements inside the lambda
        # then the tuple is just thrown away
        monitor.signals.collector_booted.connect(lambda: (self._stop_timer(), self.accept()))
        print("starting boot thread")
        self.parent.thread_pool.start(monitor)

    def _stop_timer(self):
        self.timer.stop()


class ConfirmSerialConfigDialog(QDialog):

    def __init__(self, confirm_object: ConfirmSerialConfig, thread_pool, parent=None):
        super().__init__(parent)
        self.thread_started = False

        confirm_object.signals.confirmed.connect(self.accept)
        self.worker = ConfirmSerialConfigWorker(confirm_object)

        self.setWindowTitle("LWTest - Serial Config")

        self.main_layout = QVBoxLayout()
        self.pb_layout = QHBoxLayout()
        self.button_layout = QHBoxLayout()

        self.info_label = QLabel("Waiting for the collector to register the new serial numbers.")

        self.pb = QProgressBar()
        self.pb.setAlignment(Qt.AlignHCenter)
        self.pb.setMinimum(0)
        self.pb.setMaximum(0)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.info_label, alignment=Qt.AlignHCenter)
        self.pb_layout.addWidget(self.pb)
        self.button_layout.addWidget(self.button_box, alignment=Qt.AlignHCenter)

        self.main_layout.addLayout(self.pb_layout)
        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)

        thread_pool.start(self.worker)


class CountDownDialog(QDialog):
    def __init__(self, parent, title: str, message: str, timeout: int):
        super().__init__(parent=parent)
        self.setWindowTitle(title)

        self.parent = parent
        self.message = message
        self.timeout = timeout

        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.description_label = QLabel(self.message)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.timeout)
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

    def timer_timeout(self):
        self.timeout -= 1
        if self.timeout > 0:
            self.progress_bar.setValue(self.timeout)
        else:
            self.timer.stop()
            self.accept()


class UpgradeDialog(QDialog):
    def __init__(self, serial_number: str, row: int, worker: UpgradeWorker, thread_starter: Callable, browser, parent):
        super().__init__(parent=parent)
        self.signals = UpgradeSignals()
        self.serial_number = serial_number
        self.row = row
        self.worker = worker
        self.thread_starter = thread_starter
        self.browser = browser
        self.upgrade_started = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(30)

        self.description = QLabel(f"Upgrading Sensor {self.serial_number}:\t\t\t\t")
        self.main_layout.addWidget(self.description)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignHCenter)
        self.progress.setMinimum(0)
        self.progress.setMaximum(57)
        self.progress.setValue(0)
        self.main_layout.addWidget(self.progress)

        # self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        # self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)
        # self.button_box.rejected.connect(self.reject)
        # self.main_layout.addWidget(self.button_box)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Software Upgrade")

        self.worker.signals.upgrade_failed_to_enter_program_mode.connect(self.reject)
        self.worker.signals.upgrade_progress.connect(self._update_percentage)

    def closeEvent(self, QCloseEvent):
        QCloseEvent.ignore()

    def showEvent(self, QShowEvent):
        if not self.upgrade_started:
            settings = QSettings()

            self.browser.get(LWT.URL_UPGRADE)
            if "Please reload after a moment" in self.browser.page_source:
                self.browser.get(LWT.URL_UPGRADE)

            self.browser.find_element_by_xpath(constants.unit_select_button[self.row]).click()
            self.browser.find_element_by_xpath(constants.firmware_file).send_keys(
                "LWTest/resources/firmware/firmware-0x0075.zip")
            self.browser.find_element_by_xpath(constants.upgrade_password).send_keys(
                settings.value('main/config_password'))
            self.browser.find_element_by_xpath(constants.upgrade_button).click()

            self.thread_starter(self.worker)

            self.upgrade_started = True

    def _update_percentage(self, percentage: int):
        if percentage == -1:
            self.accept()

        value = self.progress.value()
        self.progress.setValue(value + percentage)


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

    def showEvent(self, QShowEvent):
        if not self.timer.isActive():
            self.timer.start(1000)

    def _timer_timeout(self):
        self.timeout -= 1
        if self.timeout < 1:
            self.timer.stop()
            self.accept()
