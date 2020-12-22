from typing import Callable

from PyQt5.QtWidgets import QTableWidget, QComboBox, QHeaderView

import LWTest.gui.main_window.helper as helper
from LWTest.constants import lwt


def setup_table(parent, table: QTableWidget, calibrated_override: Callable,
                fault_current_override: Callable, rows=6):
    headers = ["Serial Number", "\t\t\t\t\t\tRSSI\t\t\t\t\t\t", "Firmware", "Reporting Data",
               "Calibration",
               "\t\t\t\t\t\t13.8K\t\t\t\t\t\t", "\t\t\t\t120A\t\t\t\t", "Power Factor", "Real Power",
               "\t\t\t\t\t\t7.2K\t\t\t\t\t\t", "\t\t\t\t\t60A\t\t\t\t\t", "Power Factor", "Real Power",
               "Scale Current", "Scale Voltage", "Correction Angle", "\t\tPersists\t\t\t\t",
               "Temperature", "Fault Current"]

    table.clear()
    table.setRowCount(rows)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)

    # for index, number in enumerate(serial_numbers):
    for index in range(0, rows):
        item = helper.create_item()
        item.setFlags(item.flags() | helper.Qt.ItemIsSelectable)
        table.setItem(index, 0, item)

        # Four stock QTableWidgetItems
        for column in range(lwt.TableColumn.SERIAL_NUMBER.value, lwt.TableColumn.REPORTING.value + 1):
            item = helper.create_item("---")
            table.setItem(index, column, item)

        # A "custom" cellWidget
        cal_combo = QComboBox(parent)
        cal_combo.insertItems(0, ["NA", "Pass", "Fail"])
        cal_combo.currentTextChanged.connect(lambda text, index_=index: calibrated_override(text, index_))
        table.setCellWidget(index, lwt.TableColumn.CALIBRATION.value, cal_combo)

        # Thirteen more stock QTableWidgetItems
        for column in range(lwt.TableColumn.HIGH_VOLTAGE.value, lwt.TableColumn.TEMPERATURE.value + 1):
            item = helper.create_item("---")
            table.setItem(index, column, item)

        fault_combo = QComboBox(parent)
        fault_combo.insertItems(0, ["NA", "Pass", "Fail"])
        fault_combo.currentTextChanged.connect(lambda text, index_=index: fault_current_override(text, index_))
        table.setCellWidget(index, lwt.TableColumn.FAULT_CURRENT.value, fault_combo)

    table.setCurrentCell(0, 0)
    table.resizeColumnsToContents()
