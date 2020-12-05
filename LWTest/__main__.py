import sys

from LWTest.gui.main_window.mainwindow import MainWindow

# import LWTest.patchexceptionhook as patch


def main(app):
    # patch.patch_exception_hook()
    # noinspection PyUnusedLocal
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
