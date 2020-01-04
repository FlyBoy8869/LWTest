from PyQt5.QtCore import QObject, pyqtSignal


class MainWindowSignals(QObject):
    file_dropped = pyqtSignal(str)
    adjust_size = pyqtSignal()
    serial_numbers_imported = pyqtSignal(tuple)
    collector_configured = pyqtSignal(tuple)


class WorkerSignals(QObject):
    configured_serial_numbers = pyqtSignal(tuple)
    url_read_exception = pyqtSignal(tuple)
    serial_config_page_failed_to_load = pyqtSignal(str, tuple)
    successful_link = pyqtSignal(tuple)
    link_timeout = pyqtSignal(tuple)  # emits the serial numbers that did not link to the collector

    upgrade_successful = pyqtSignal(str)
    upgrade_failed_to_enter_program_mode = pyqtSignal(int)
    upgrade_show_activity = pyqtSignal(int)
    upgrade_timed_out = pyqtSignal(str)

    link_activity = pyqtSignal(tuple, str)

    resize_columns = pyqtSignal()


class CollectorSignals(QObject):
    data_reading = pyqtSignal(tuple, str)
    fault_current = pyqtSignal(str)
    data_persisted = pyqtSignal(str, int, int)


class FirmwareSignals(QObject):
    firmware_version = pyqtSignal(tuple, str)
