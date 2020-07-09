import sys

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from LWTest.config.app import settings, logging


def main():
    args = sys.argv
    app = QApplication(args)
    # app.setStyle('Fusion')
    settings.load(r"LWTest/resources/config/config.txt", QSettings())
    settings.process_command_line_args(args, QSettings())
    logging.initialize()
    # import moved here for compatibility with Linux;
    # it won't work at the top of the file for Linux, but does for macOS and Windows
    from LWTest.gui.main_window.main_window import MainWindow
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
