from PyQt6 import QtGui
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QTableWidget


class LWTTableWidget(QTableWidget):
    class Signals(QObject):
        double_clicked = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = self.Signals()

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if (item := self.indexAt(e.pos())) and item.column() == 0:
                self.signals.double_clicked.emit(item.row())

            e.accept()
        else:
            e.ignore()
