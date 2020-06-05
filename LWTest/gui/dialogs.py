from time import sleep
from typing import Callable

import requests
from PyQt5.QtCore import QTimer, QRunnable, QObject, pyqtSignal, Qt, QSettings, QCoreApplication
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout, QDialogButtonBox, QMessageBox, \
    QWidget

import LWTest.spreadsheet.spreadsheet as spreadsheet
import LWTest.LWTConstants as LWT
from LWTest.collector.read.confirm import ConfirmSerialConfig
from LWTest.constants import dom
from LWTest.utilities import file
from LWTest.workers.confirm import ConfirmSerialConfigWorker
from LWTest.workers.upgrade import UpgradeWorker
from LWTest.spreadsheet.constants import phases, PhaseReadings
import LWTest.utilities.returns as returns
import LWTest.utilities.time as util_time


class Signals(QObject):
    collector_booted = pyqtSignal()


class UpgradeSignals(QObject):
    cancelled = pyqtSignal()


class PersistenceBootMonitor(QDialog):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Persistence")

        self.parent = parent
        # self._url = LWT_constants.URL_RAW_CONFIGURATION
        self.timeout = LWT.TimeOut.COLLECTOR_BOOT_WAIT_TIME.value

        self.thread_started = False
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.description_label = QLabel("Please, wait for the collector to boot.\t\t")

        progress_bar_stylesheet = "QProgressBar {min-height: 10px; max-height: 10px}"
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(progress_bar_stylesheet)
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

    def closeEvent(self, QCloseEvent):
        QCloseEvent.ignore()

    def showEvent(self, QShowEvent):
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

    def showEvent(self, QShowEvent):
        if not self.timer.isActive():
            self.timer.start(1000)

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
        super().__init__(parent=parent)
        self._spreadsheet_path = spreadsheet_path
        self._sensors = sensors
        self._room_temperature = room_temperature

        self.setWindowTitle("LWTest - Saving Sensor Data")

        palette = QPalette()
        palette.setColor(QPalette.Background, Qt.white)
        self.setPalette(palette)

        self.setLayout(QVBoxLayout())

        self._main_layout = QHBoxLayout()
        self.layout().addLayout(self._main_layout)

        self._main_label = QLabel("Saving sensor data to spreadsheet.", self)
        font = self._main_label.font()
        font.setPointSize(9)
        self._main_label.setFont(font)
        self._main_layout.addWidget(self._main_label, alignment=Qt.AlignHCenter)

        self._sub_layout = QHBoxLayout()
        self.layout().addLayout(self._sub_layout)

        self._sub_label = QLabel("Please, wait...", self)
        self._sub_label.setFont(font)
        self._sub_label.setStyleSheet("padding-top: 10px;")
        self._sub_layout.addWidget(self._sub_label, alignment=Qt.AlignHCenter)

    def showEvent(self, QShowEvent):
        QTimer().singleShot(1000, self._save_data)

    def _save_data(self):
        data_sets = []
        data = []
        for index, unit in enumerate(self._sensors):
            for field in self._DATA_IN_SPREADSHEET_ORDER:
                data.append(unit.__getattribute__(field))

            phase = PhaseReadings(*phases[index])
            data_to_save = zip(phase, data)
            dts = list(data_to_save)

            data_sets.append(dts)
            data = []

        if not spreadsheet.save_sensor_data(self._spreadsheet_path, data_sets, self._room_temperature):
            self.reject()

        self._main_label.setText("Downloading log files from the collector.")
        QCoreApplication.processEvents()  # so the change to the label above shows up

        result = self._download_log_files()
        if not result.success:
            self._report_log_file_download_failure(result.error)
            self.reject()
            return

        spreadsheet.record_log_files_attached(self._spreadsheet_path)

        self.accept()

    def _download_log_files(self) -> returns.Result:
        return file.download_log_files(file.create_log_filename_from_spreadsheet_path(self._spreadsheet_path))

    def _report_log_file_download_failure(self, detail_text):
        msg_box = QMessageBox(QMessageBox.Warning, "LWTest - Saving Log Files",
                              "An error occurred trying to download the log files.", QMessageBox.Ok,
                              self)
        msg_box.setDetailedText(detail_text)
        msg_box.exec()
