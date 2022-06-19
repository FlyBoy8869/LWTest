from PyQt6.QtWidgets import QDialog

from LWTest.dialogs.save import SaveDialog
from LWTest.sensor import SensorLog
from LWTest.utilities import file_utils


class DataSaver:
    def __init__(self, parent, spreadsheet_path: str, sensor_log: SensorLog, refs):
        self._parent = parent
        self._spreadsheet_path = spreadsheet_path
        self._sensor_log = sensor_log
        self._refs = refs

    def save(self):
        log_file_path = file_utils.create_log_filename(
            self._spreadsheet_path, self._sensor_log.get_serial_numbers_as_tuple()
        )

        high_refs, low_refs = self._sensor_log.references
        if not self._sensor_log.have_references:
            high_refs, low_refs = self._refs.get_references()

            if high_refs is None:
                return

        save_data_dialog = SaveDialog(
            self._parent,
            self._spreadsheet_path,
            log_file_path, iter(self._sensor_log),
            (self._sensor_log.room_temperature,
             high_refs,
             low_refs)
        )
        if save_data_dialog.exec() == QDialog.DialogCode.Accepted:
            return True

        return False
