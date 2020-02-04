from PyQt5.QtCore import QRunnable, QSettings

from LWTest.collector.read.confirm import ConfirmSerialConfig


class ConfirmSerialConfigWorker(QRunnable):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def run(self):
        self.payload.read()


def confirm_serial_update(serial_numbers: tuple):
    settings = QSettings()
    url = settings.value("pages/modem_status")

    confirm_serial_config = ConfirmSerialConfig(serial_numbers, url)

    return ConfirmSerialConfigWorker(confirm_serial_config)
