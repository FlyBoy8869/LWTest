from time import sleep

from PyQt5.QtCore import QRunnable, QObject, pyqtSignal


class Signals(QObject):
    finished = pyqtSignal()


class PostLinkCheckWorker(QRunnable):
    def __init__(self, readers):
        super().__init__()
        self.signals = Signals()
        self.readers = readers

    def run(self):
        for reader in self.readers:
            reader.read()
        sleep(1)
        self.signals.finished.emit()
