from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QSettings
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from selenium.common.exceptions import WebDriverException
from typing import Callable

from LWTest.constants import lwt_constants, dom
from LWTest.workers.upgrade import UpgradeWorker


class UpgradeDialog(QDialog):
    error = pyqtSignal(str)

    def __init__(self, serial_number: str, row: int, worker: UpgradeWorker, thread_starter: Callable, browser, parent):
        super().__init__(parent=parent)
        self.serial_number = serial_number
        self.row = row
        self.worker = worker
        self.thread_starter = thread_starter
        self.browser = browser
        self.upgrade_started = False

        self.browser_error = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(30)

        self.description = QLabel(f"Upgrading Sensor {self.serial_number}:\t\t\t\t")
        self.main_layout.addWidget(self.description)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignHCenter)
        self.progress.setMinimum(0)
        self.progress.setMaximum(83)
        self.progress.setValue(0)
        self.main_layout.addWidget(self.progress)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Software Upgrade")

        self.worker.signals.upgrade_failed_to_enter_program_mode.connect(self.reject)
        self.worker.signals.upgrade_progress.connect(self._update_percentage)

        QTimer.singleShot(300, self._kick_off)

    def closeEvent(self, q_close_event):
        if self.browser_error:
            q_close_event.accept()
        else:
            q_close_event.ignore()

    def _kick_off(self):
        if not self.upgrade_started:
            settings = QSettings()

            try:
                self.browser.get(lwt_constants.URL_SOFTWARE_UPGRADE)
            except WebDriverException as error:
                print(f"error: {error.msg}")
                self.browser_error = True
                self.done(QDialog.Rejected)
                self.error.emit(error.msg)
                return

            if "Please reload after a moment" in self.browser.page_source:
                self.browser.get(lwt_constants.URL_SOFTWARE_UPGRADE)

            self.browser.find_element_by_xpath(dom.unit_select_button[self.row]).click()
            self.browser.find_element_by_xpath(dom.firmware_file).send_keys(
                "/Users/charles/PycharmProjects/LWTest/LWTest/resources/firmware/firmware-0x0075.zip")
            self.browser.find_element_by_xpath(dom.upgrade_password).send_keys(
                settings.value('main/config_password'))
            self.browser.find_element_by_xpath(dom.upgrade_button).click()

            self.thread_starter(self.worker)

            self.upgrade_started = True

    def _update_percentage(self, percentage: int):
        if percentage == -1:
            self.accept()

        value = self.progress.value()
        self.progress.setValue(value + percentage)
