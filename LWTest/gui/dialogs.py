from time import sleep
from typing import Callable

import requests
from PyQt5.QtCore import QTimer, QRunnable, QObject, pyqtSignal, Qt, QSettings, QCoreApplication
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout, QDialogButtonBox, QMessageBox

import LWTest.LWTConstants as LWT
import LWTest.spreadsheet.spreadsheet as spreadsheet
import LWTest.utilities.returns as returns
import LWTest.utilities.time as util_time
from LWTest.common import oscomp
from LWTest.common.oscomp import OSType
from LWTest.constants import dom
from LWTest.spreadsheet.constants import phases_cells, PhaseReadingsCells
from LWTest.utilities import file_utils
from LWTest.workers.upgrade import UpgradeWorker


class Signals(QObject):
    collector_booted = pyqtSignal()
    dialog_timed_out = pyqtSignal()


class UpgradeSignals(QObject):
    cancelled = pyqtSignal()


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
                if 200 == requests.get(self._url, timeout=LWT.TimeOut.URL_REQUEST.value).status_code:
                    self.signals.collector_booted.emit()
                    sleep(1)
                    return
            except requests.exceptions.RequestException:
                print("unable to load raw config page")

            sleep(1)
            self._timeout -= 1

        self.signals.dialog_timed_out.emit()


class PersistenceBootMonitor(QDialog):

    def __init__(self, parent, thread_pool):
        super().__init__(parent=parent)
        self.setWindowTitle("Persistence")

        self.parent = parent
        self._thread_pool = thread_pool
        self.timeout = LWT.TimeOut.COLLECTOR_BOOT_WAIT_TIME.value

        self._need_to_start_thread: bool = True
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.description_label = QLabel("Please, wait for the collector to boot.\t\t")

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar {min-height: 10px; max-height: 10px}")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setTextVisible(False)

        self.main_layout.addWidget(self.description_label)
        self.main_layout.addWidget(self.progress_bar)

        self.setLayout(self.main_layout)

    def showEvent(self, q_show_event):
        if self._need_to_start_thread:
            self._need_to_start_thread = False
            self._wait_for_collector_to_boot()

    def _wait_for_collector_to_boot(self):
        monitor = PageReachable(LWT.URL_RAW_CONFIGURATION, self.timeout)
        monitor.signals.collector_booted.connect(self.accept)
        monitor.signals.dialog_timed_out.connect(self.reject)
        self._thread_pool.start(monitor)


class ConfirmSerialConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
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
        self.progress.setMaximum(83)
        self.progress.setValue(0)
        self.main_layout.addWidget(self.progress)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Software Upgrade")

        self.worker.signals.upgrade_failed_to_enter_program_mode.connect(self.reject)
        self.worker.signals.upgrade_progress.connect(self._update_percentage)

    def closeEvent(self, q_close_event):
        q_close_event.ignore()

    def showEvent(self, q_show_event):
        if not self.upgrade_started:
            settings = QSettings()

            self.browser.get(LWT.URL_UPGRADE)
            if "Please reload after a moment" in self.browser.page_source:
                self.browser.get(LWT.URL_UPGRADE)

            self.browser.find_element_by_xpath(dom.unit_select_button[self.row]).click()
            self.browser.find_element_by_xpath(dom.firmware_file).send_keys(
                "LWTest/resources/firmware/firmware-0x0075.zip")
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


class SaveDataDialog(QDialog):
    _DATA_IN_SPREADSHEET_ORDER = ("high_voltage", "high_current", "high_power_factor", "high_real_power",
                                  "low_voltage", "low_current", "low_power_factor", "low_real_power",
                                  "scale_current", "scale_voltage", "correction_angle", "persists",
                                  "firmware_version", "reporting_data", "rssi", "calibrated",
                                  "temperature", "fault_current")

    file_name_prefix = "ATR-PRD#-"
    file_name_serial_number_template = "-SN{}"

    def __init__(self, parent, spreadsheet_path: str, sensors: iter, room_temperature: str):
        super().__init__(parent)
        self.setWindowTitle("LWTest - Saving Sensor Data")

        self._spreadsheet_path = spreadsheet_path
        self._sensors = sensors
        self._room_temperature = room_temperature

        self.setLayout(QVBoxLayout())

        self._top_layout = QVBoxLayout()
        self.layout().addLayout(self._top_layout)

        self._main_label = QLabel("Saving sensor data to spreadsheet.", self)
        font = self._main_label.font()
        point_size = 9 if oscomp.os_type == OSType.WINDOWS else 13
        font.setPointSize(point_size)
        self._main_label.setFont(font)
        self._top_layout.addWidget(self._main_label, alignment=Qt.AlignHCenter)

        horizontal_spacer = QLabel("\t\t\t\t\t", self)
        self._top_layout.addWidget(horizontal_spacer, alignment=Qt.AlignHCenter)

        self._bottom_layout = QHBoxLayout()

        self._sub_label = QLabel("Please, wait...", self)
        self._sub_label.setFont(font)

        self._bottom_layout.addWidget(self._sub_label, alignment=Qt.AlignHCenter)

        self.layout().addLayout(self._bottom_layout)

    def showEvent(self, q_show_event):
        QTimer().singleShot(1000, self._save_data)

    def _package_data(self):
        data_sets = []
        data = []
        for index, unit in enumerate(self._sensors):
            for field in self._DATA_IN_SPREADSHEET_ORDER:
                data.append(unit.__getattribute__(field))

            phase_cells = PhaseReadingsCells(*phases_cells[index])
            data_packet = list(zip(phase_cells, data))
            data_sets.append(data_packet)
            data = []

        return data_sets

    def _save_data(self):
        if not (result := spreadsheet.save_sensor_data(self._spreadsheet_path,
                                                       self._package_data(),
                                                       self._room_temperature)).success:
            self._report_failure("A problem occurred while saving readings to the spreadsheet", result.error)
            self.reject()

        if not (result := self._download_log_files()).success:
            self._report_failure("An error occurred trying to download the log files.", result.error)
            self.reject()
            return
        else:
            spreadsheet.record_log_files_attached(self._spreadsheet_path)

        self.accept()

    def _download_log_files(self) -> returns.Result:
        self._main_label.setText("Downloading log files from the collector.")
        QCoreApplication.processEvents()  # so the change to the label above shows up

        result: returns.Result = file_utils.download_log_files(
            file_utils.create_log_filename_from_spreadsheet_path(self._spreadsheet_path)
        )
        return result

    def _report_failure(self, message, detail_text):
        msg_box = QMessageBox(QMessageBox.Warning, "LWTest - Saving Log Files",
                              message, QMessageBox.Ok,
                              self)
        msg_box.setDetailedText(detail_text)
        msg_box.exec()
