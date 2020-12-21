import io
import sys

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMessageBox

_original_hook = sys.excepthook
_original_stderr = sys.stderr

_text_buffer = io.StringIO()


def excepthook(exc_type, exc_value, traceback_obj):
    # "redirect" stderr to an in memory buffer in order to capture output of sys.excepthook() for use in GUI message
    sys.stderr = _text_buffer
    _original_hook(exc_type, exc_value, traceback_obj)

    # This is for me using PyCharm.
    # It will cause the traceback to be printed in the "Run" window,
    # providing a clickable link to the offending line.
    print(_text_buffer.getvalue(), file=_original_stderr)

    # make traceback visible in GUI
    font = QFont("non-existent")
    font.setStyleHint(QFont.TypeWriter)
    error_box = QMessageBox()
    error_box.setFont(font)
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle("Warning: Something Wicked This Way Comes...\t\t\t\t\t\t\t\t\t")
    error_box.setText("<h2>An unhandled exception occurred.</h2>")
    error_box.setDetailedText(_text_buffer.getvalue())
    error_box.exec()

    # prevent accumulation of messages cluttering output
    _text_buffer.truncate(0)

    sys.stderr = _original_stderr


def patch_exception_hook():
    sys.excepthook = excepthook
