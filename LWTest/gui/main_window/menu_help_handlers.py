from PyQt6.QtWidgets import QMessageBox

import LWTest


def menu_help_about_handler(parent=None):
    app_title = LWTest.app_title.split('-', 1)[0].strip()
    text = f"<div><h1>{app_title}</h1></div><div style='margin-top: 2em;'><p>Version: {LWTest.version}</p>\
    <p>Author: Charles Cognato</p><p>email: charlescognato@gmail.com</p></div>"
    QMessageBox.about(parent, f"{app_title}\t\t\t\t\t\t", text)
