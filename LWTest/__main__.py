import sys

from LWTest.gui.main_window.main_window import MainWindow


def main(app):
    # noinspection PyUnusedLocal
    window = MainWindow()
    sys.exit(app.exec_())
