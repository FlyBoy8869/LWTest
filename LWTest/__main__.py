import sys

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from LWTest.config.app import settings, logging


def main():
    args = sys.argv
    app = QApplication(args)
    settings.load(r"LWTest/resources/config/config.txt", QSettings())
    settings.process_command_line_args(args, QSettings())
    logging.initialize()
    from LWTest.gui.main_window.main_window import MainWindow
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
