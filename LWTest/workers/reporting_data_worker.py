from PyQt5.QtCore import QRunnable


class ReportingDataWorker(QRunnable):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def run(self):
        self.payload.read()
