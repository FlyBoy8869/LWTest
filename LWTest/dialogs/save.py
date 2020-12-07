from PyQt5.QtCore import Qt, QTimer
from pathlib import Path

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox

from LWTest.spreadsheet import spreadsheet as spreadsheet
from LWTest.spreadsheet.constants import PhaseReadingsCells, phases_cells
from LWTest.utilities import file_utils, oscomp
from LWTest.utilities.oscomp import OSBrand


class SaveDialog(QDialog):
    _DATA_IN_SPREADSHEET_ORDER = ("high_voltage", "high_current", "high_power_factor", "high_real_power",
                                  "low_voltage", "low_current", "low_power_factor", "low_real_power",
                                  "scale_current", "scale_voltage", "correction_angle", "persists",
                                  "firmware_version", "reporting_data", "rssi", "calibrated",
                                  "temperature", "fault_current")

    file_name_prefix = "ATR-PRD#-"
    file_name_serial_number_template = "-SN{}"

    def __init__(self, parent, spreadsheet_path: str, log_file_path: Path, sensors: iter, references):
        super().__init__(parent)
        self.setWindowTitle("LWTest - Saving Sensor Data")

        self._spreadsheet_path = spreadsheet_path
        self._log_file_path = log_file_path
        self._sensors = sensors
        self._references = references

        self.setLayout(QVBoxLayout())

        self._top_layout = QVBoxLayout()
        self.layout().addLayout(self._top_layout)

        self._main_label = QLabel("Saving sensor data to spreadsheet.", self)
        font = self._main_label.font()
        point_size = 9 if oscomp.os_brand == OSBrand.WINDOWS else 13
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

        QTimer().singleShot(500, self._save_data)

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
        if self._do_save():
            self._main_label.setText("Downloading log files from the collector.")
            QTimer.singleShot(1000, self._download_log_files)
        else:
            self.reject()

    def _do_save(self):
        result = spreadsheet.save_test_results(self._spreadsheet_path, self._package_data(), self._references)
        if not result.success:
            self._report_failure("A problem occurred while saving readings to the spreadsheet", result.error)
            return False
        return True

    def _download_log_files(self):
        if not (result := file_utils.download_log_files(self._log_file_path)).success:
            self._report_failure("An error occurred trying to download the log files.", result.error)
            self.reject()
        else:
            spreadsheet.record_log_files_attached(self._spreadsheet_path)
            self.accept()

    def _report_failure(self, message, detail_text):
        msg_box = QMessageBox(
            QMessageBox.Warning, "LWTest - Saving Log Files", message, QMessageBox.Ok, self
        )
        msg_box.setDetailedText(detail_text)
        msg_box.exec()
