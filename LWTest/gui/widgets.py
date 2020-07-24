from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QModelIndex
from PyQt5.QtWidgets import QTableWidget


class LWTTableWidget(QTableWidget):
    class Signals(QObject):
        double_clicked = pyqtSignal(int, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = self.Signals()

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == Qt.LeftButton:
            if (item := self.indexAt(e.pos())) and item.column() == 0:
                serial_number = self.item(item.row(), item.column()).text()
                self.signals.double_clicked.emit(item.row(), serial_number)

            e.accept()
        else:
            e.ignore()
