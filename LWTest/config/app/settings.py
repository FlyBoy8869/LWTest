# settings.py
import re

from PyQt5.QtCore import QSettings, QCoreApplication


org_name = "Medium Voltage Sensors"
app_name = "LWTest"

QCoreApplication.setOrganizationName(org_name)
QCoreApplication.setApplicationName(app_name)


def load(args, repository, path):
    _load_settings(path, repository)
    _process_command_line_args(args, repository)


def _load_settings(path: str, settings: QSettings):
    with open(path) as in_f:
        for setting in in_f.readlines():
            if not setting.strip() or setting.startswith("#"):
                continue
            setting = setting.strip().split("=", 1)
            print(f"creating setting: {setting}")
            settings.setValue(setting[0], setting[1])


def _process_command_line_args(args: list, settings: QSettings):
    debug = True if "DEBUG" in args else False
    settings.setValue("DEBUG", debug)

    server = "127.0.0.1"
    pattern = re.compile(r"server=(\d+.\d+.\d+.\d+)")
    for arg in args:
        match = pattern.match(arg)
        if match:
            server = match[1]
    settings.setValue("server", server)
