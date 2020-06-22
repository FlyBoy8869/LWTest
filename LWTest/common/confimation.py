from PyQt5.QtWidgets import QMessageBox


class ChangeTracker:
    def __init__(self):
        self._unsaved_changes = False

    def discard_test_results(self, parent, clear_flag=True):
        if self._unsaved_changes:
            button = QMessageBox.question(parent, "Unsaved Test Results",
                                          "Discard results?\t\t\t\t",
                                          QMessageBox.Yes | QMessageBox.No,
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
