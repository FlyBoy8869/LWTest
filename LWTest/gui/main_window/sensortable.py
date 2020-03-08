from typing import Callable

from PyQt5.QtWidgets import QTableWidget, QComboBox, QHeaderView

import LWTest.gui.main_window.helper as helper
import LWTest.LWTConstants as LWT


def setup_table_widget(parent, serial_numbers: tuple, table: QTableWidget, calibrated_override: Callable,
                       fault_current_override: Callable):
    headers = ["Serial Number", "\t\t\t\t\t\tRSSI\t\t\t\t\t\t", "Firmware", "Reporting Data",
               "Calibration",
               "\t\t\t\t\t\t13.8K\t\t\t\t\t\t", "\t\t\t\t120A\t\t\t\t", "Power Factor", "Real Power",
               "\t\t\t\t\t\t7.2K\t\t\t\t\t\t", "\t\t\t\t\t60A\t\t\t\t\t", "Power Factor", "Real Power",
               "Scale Current", "Scale Voltage", "Correction Angle", "\t\tPersists\t\t\t\t",
               "Temperature", "Fault Current"]

    table.clear()
    table.setRowCount(len(serial_numbers))
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

    for index, number in enumerate(serial_numbers):
        item = helper.create_item(number)
        item.setFlags(item.flags() | helper.Qt.ItemIsSelectable)
        table.setItem(index, 0, item)

        # Three stock QTableWidgetItems
        for column in range(LWT.TableColumn.RSSI.value, LWT.TableColumn.REPORTING.value + 1):
            item = helper.create_item()
            table.setItem(index, column, item)

        # A "custom" cellWidget
        cal_combo = QComboBox(parent)
        cal_combo.insertItems(0, ["NA", "Pass", "Fail"])
        cal_combo.currentTextChanged.connect(lambda text, index=index: calibrated_override(text, index))
        table.setCellWidget(index, LWT.TableColumn.CALIBRATION.value, cal_combo)

        # Thirteen more stock QTableWidgetItems
        for column in range(LWT.TableColumn.HIGH_VOLTAGE.value, LWT.TableColumn.TEMPERATURE.value + 1):
            item = helper.create_item()
            table.setItem(index, column, item)

        fault_combo = QComboBox(parent)
        fault_combo.insertItems(0, ["NA", "Pass", "Fail"])
        fault_combo.currentTextChanged.connect(lambda text, index=index: fault_current_override(text, index))
        table.setCellWidget(index, LWT.TableColumn.FAULT_CURRENT.value, fault_combo)

    table.setCurrentCell(0, 0)
    table.resizeColumnsToContents()
