from PyQt5.QtWidgets import QMessageBox


class ChangeTracker:
    def __init__(self):
        self._unsaved_changes = False

    @property
    def is_changes(self):
        return self._unsaved_changes

    def can_discard(self, *, parent, clear_flag=True):
        if self._unsaved_changes:
            button = QMessageBox.question(parent, "Unsaved Test Results",
                                          "Discard results?\t\t\t\t",
                                          QMessageBox.Discard | QMessageBox.No,
                                          QMessageBox.No)

            if button == QMessageBox.No:
                return False

        if clear_flag:
            self._unsaved_changes = False

        return True

    def set_change_flag(self):
        self._unsaved_changes = True

    def clear_change_flag(self):
        self._unsaved_changes = False
