from PyQt5.QtCore import QRunnable


class FaultCurrentWorker(QRunnable):
    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def run(self):
        self.payload.read()
