import shutil

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QDialog, QLineEdit, QFileDialog
from pathlib import Path
from typing import cast, Optional

from LWTest.gui.createset.createset_ui import Ui_Dialog
from LWTest.spreadsheet import spreadsheet

TEST_RECORD = "LWTest/resources/testrecord/ATR-PRD Master.xlsm"


class CreateSetDialog(QDialog, Ui_Dialog):

    def __init__(self, parent, *, prefix="980"):
        super().__init__(parent)
        self.setupUi(self)

        self._prefix = prefix

        self.input_1.setText(prefix)

        self.input_1.installEventFilter(self)
        self.input_2.installEventFilter(self)
        self.input_3.installEventFilter(self)
        self.input_4.installEventFilter(self)
        self.input_5.installEventFilter(self)
        self.input_6.installEventFilter(self)

        # used for up and down arrow movement
        self._active_field = 0

        # tracks visible input fields
        self._field_index = 0
        self._input_fields = [
            self.input_1, self.input_2, self.input_3,
            self.input_4, self.input_5, self.input_6
        ]
        self._hide_fields()

        self.buttonAdd.clicked.connect(self._add_input_field)
        self.buttonRemove.clicked.connect(self._remove_input_field)

        self.setFixedSize(self.size())

    @property
    def serial_numbers(self):
        """Returns list of serial numbers, or None if an invalid entry is found."""
        return self._get_serial_numbers()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(widget, (QLineEdit,)) and event.type() == QtCore.QEvent.KeyPress:
            key_event: QtGui.QKeyEvent = cast(QtGui.QKeyEvent, event)
            key = key_event.key()
            if key == Qt.Key_Up or key == Qt.Key_Down:
                self.keyPressEvent(key_event)
                return True

        return False

    def keyPressEvent(self, key_event: QtGui.QKeyEvent) -> None:
        if key_event.key() == Qt.Key_Tab and key_event.modifiers() == Qt.AltModifier:
            self._move_to_previous_field()
        elif key_event.key() == Qt.Key_Tab:
            self._add_input_field()
        elif key_event.key() == Qt.Key_R and key_event.modifiers() == Qt.ControlModifier:
            self._remove_input_field()
        elif key_event.key() == Qt.Key_Up:
            self._move_to_previous_field()
        elif key_event.key() == Qt.Key_Down:
            self._move_to_next_field()
        else:
            super().keyPressEvent(key_event)

    def _add_input_field(self):
        if self._field_index < 5:
            self._field_index += 1
            self._active_field = self._field_index
            field = self._input_fields[self._field_index]
            field.setVisible(True)
            field.setFocus()
            if not field.text():
                field.setText(self._prefix)
        else:
            # just do regular tab behavior
            self._move_to_next_field()

    def _remove_input_field(self):
        self._hide_field()

    def _hide_fields(self):
        for field in self._input_fields[1:]:
            field.setVisible(False)

        self._input_fields[0].setFocus()

    def _hide_field(self):
        if self._field_index > 0:
            field = self._input_fields[self._field_index]
            field.setVisible(False)
            field.clear()

            if self._active_field == self._field_index:
                self._move_to_previous_field()

            self._field_index -= 1

    def _move_to_previous_field(self):
        if self._active_field > 0:
            self._active_field -= 1
            field = self._input_fields[self._active_field]
            field.setFocus()
            field.end(False)

    def _move_to_next_field(self):
        if self._active_field < 5 and self._input_fields[self._active_field + 1].isVisible():
            self._active_field += 1
            field = self._input_fields[self._active_field]
            field.setFocus()
            field.end(False)

    def _get_serial_numbers(self):
        # never mind
        if self.result() == QDialog.Rejected:
            return None

        serial_numbers = []
        for index in range(0, self._field_index + 1):
            serial_numbers.append(self._input_fields[index].text())

        # user just decided to hit 'Ok' instead of 'Cancel' after opening dialog
        if "980" in serial_numbers:
            return None

        # numbers only, please
        try:
            for serial_number in serial_numbers:
                int(serial_number)
        except ValueError:
            return None

        return serial_numbers


def _enter_set_serial_numbers(parent):
    (create_set_dialog := CreateSetDialog(parent)).exec()
    return create_set_dialog.serial_numbers


def _copy_test_record_to_folder(dst: str) -> str:
    return shutil.copy(TEST_RECORD, dst)


def _put_serial_numbers_in_test_record(serial_numbers, path):
    spreadsheet.create_test_record(serial_numbers, path)


def manual_set_entry(parent) -> Optional[str]:
    serial_numbers = _enter_set_serial_numbers(parent)

    if serial_numbers:
        save_folder = QSettings().value("save_folder")
        if not Path(save_folder).exists():
            save_folder = '.'

        directory = QFileDialog.getExistingDirectory(parent, "Save to...", save_folder)
        if directory:
            path = _copy_test_record_to_folder(directory)
            _put_serial_numbers_in_test_record(serial_numbers, path)
            return path

    return None
