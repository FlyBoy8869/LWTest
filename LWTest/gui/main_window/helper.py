from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QTableWidgetItem


def create_item(text=""):
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemIsEnabled)
    item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    return item
