import sys

from PyQt5.QtWidgets import QApplication

from LWTest.gui.main_window.main_window import MainWindow
from LWTest.config.app import settings, logging


def main():
    app = QApplication([])
    window = MainWindow()
    settings.load(r"LWTest/resources/config/config.txt")
    logging.initialize()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
