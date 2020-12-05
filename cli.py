import sys

from traceback_with_variables import activate_by_import
import LWTest.patchexceptionhook as patch
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from LWTest.config.app import logging, settings
from LWTest.__main__ import main

if __name__ == '__main__':
    patch.patch_exception_hook()
    app = QApplication(sys.argv)
    settings.load(sys.argv, QSettings(), r"LWTest/resources/config/config.txt")
    logging.initialize()
    main(app)
