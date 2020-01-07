from time import sleep

import requests
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal


class ConfirmSerialConfigWorker(QRunnable):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def run(self):
        self.payload.read()
