from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem


def create_item(text=""):
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    return item
