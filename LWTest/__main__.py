import sys

from LWTest.gui.main_window.mainwindow import MainWindow


def main(app):
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
