import sys

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from LWTest.config.app import logging, settings
from LWTest.__main__ import main

if __name__ == '__main__':
    app = QApplication(sys.argv)
    settings.load(sys.argv, QSettings(), r"LWTest/resources/config/config.txt")
    logging.initialize()
    main(app)
