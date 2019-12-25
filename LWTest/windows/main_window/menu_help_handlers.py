from PyQt5.QtWidgets import QMessageBox

_title = "LWTest"
_version = "0.0.2"


def menu_help_about_handler(parent=None):
    text = f"<h1>{_title}</h1><br/>Version {_version}<br/>Author: Charles Cognato<br/>email: charlescognato@gmail.com"
    QMessageBox.about(parent, f"{_title}\t\t\t\t\t\t", text)
