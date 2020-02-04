from functools import partial

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QMessageBox

import LWTest.LWTConstants as LWT
from LWTest.sensor import SensorLog
from LWTest.workers.link import LinkWorker

_link_error = None
_sensor_linked = None
_warn_not_linked = None
_link_activity = None


def determine_link_status(sensor_log: SensorLog, sensor_table, thread_pool, parent, record_func):
    link_worker = LinkWorker(sensor_log.get_serial_numbers(), LWT.URL_MODEM_STATUS)

    global _link_error
    _link_error = partial(_link_error_handler, parent, sensor_log.get_serial_numbers())
    link_worker.signals.url_read_exception.connect(_link_error)

    global _sensor_linked
    _sensor_linked = partial(_sensor_linked_handler, parent, sensor_table, record_func)
    link_worker.signals.successful_link.connect(_sensor_linked)

    global _warn_not_linked
    _warn_not_linked = partial(_warn_sensors_not_linked_handler, parent, sensor_table)
    link_worker.signals.link_timeout.connect(_warn_not_linked)

    global _link_activity
    _link_activity = partial(_link_activity_handler, sensor_table)
    link_worker.signals.link_activity.connect(_link_activity)

    link_worker.signals.resize_columns.connect(lambda: sensor_table.resizeColumnsToContents())

    thread_pool.start(link_worker)


def _link_error_handler(parent, serial_numbers: tuple, info):
    msg_box = QMessageBox(QMessageBox.Warning,
                          "LWTest",
                          "Error while checking link status.\n\n" +
                          f"{info[1]}",
                          QMessageBox.Ok | QMessageBox.Retry, parent)

    msg_box.setDetailedText(f"{info[2]}")

    button = msg_box.exec_()

    if button == QMessageBox.Retry:
        determine_link_status(parent.sensor_log, parent.qtw_sensors, parent.thread_pool, parent,
                              parent._record_rssi_readings)


def _sensor_linked_handler(parent, sensor_table, record_func, data):
    serial_number = data[0]
    rssi = data[1]

    items = sensor_table.findItems(serial_number, Qt.MatchExactly)
    row = sensor_table.row(items[0])
    parent._update_table_with_reading((row, 1), rssi)

    record_func(serial_number, rssi)

    parent._read_post_link_data(serial_number)


def _warn_sensors_not_linked_handler(parent, sensor_table, serial_numbers):
    # responds to link_worker.link_timeout
    for serial_number in serial_numbers:
        items = sensor_table.findItems(serial_number, Qt.MatchExactly)
        if items:
            row = sensor_table.row(items[0])
            sensor_table.item(row, 1).setText("Not Linked")

            parent._record_rssi_readings(serial_number, "Not Linked")

            parent._read_post_link_data(serial_number)


def _link_activity_handler(sensor_table, serial_numbers, indicator):
    for serial_number in serial_numbers:
        items = sensor_table.findItems(serial_number, Qt.MatchExactly)
        if items:
            row = sensor_table.row(items[0])
            sensor_table.item(row, 1).setText(indicator)
