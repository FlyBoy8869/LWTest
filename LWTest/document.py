from enum import Enum, auto

from PyQt6.QtWidgets import QMessageBox


class DocumentState(Enum):
    DIRTY = auto()
    CLEAN = auto()


class Document:
    def __init__(self) -> None:
        self._dirty: DocumentState = DocumentState.CLEAN

    @property
    def is_dirty(self) -> bool:
        return self._dirty == DocumentState.DIRTY

    # QUESTION: Should this be here or in MainWindow, which is the only place it's used?
    def can_discard(self, *, parent) -> bool:
        if self.is_dirty:
            button = QMessageBox.question(
                parent,
                "Unsaved Test Results",
                "Discard results?\t\t\t\t",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if button == QMessageBox.StandardButton.No:
                return False

        self._dirty = DocumentState.CLEAN
        return True

    def __call__(self, state: DocumentState) -> None:
        self._dirty = state
