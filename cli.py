import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

import LWTest.patchexceptionhook as patch
from LWTest.__main__ import main
from LWTest.config.app import logging, settings

if __name__ == '__main__':
    patch.patch_exception_hook()
    app = QApplication(sys.argv)
    settings.load(sys.argv, QSettings(), r"LWTest/resources/config/config.txt")
    logging.initialize()
    main(app)
