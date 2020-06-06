# settings.py
from PyQt5.QtCore import QSettings, QCoreApplication


org_name = "Medium Voltage Sensors"
app_name = "LWTest"

QCoreApplication.setOrganizationName(org_name)
QCoreApplication.setApplicationName(app_name)


def load(path: str, settings: QSettings):
    with open(path) as in_f:
        for setting in in_f.readlines():
            if not setting.strip() or setting.startswith("#"):
                continue
            setting = setting.strip().split("=", 1)
            print(f"creating setting: {setting}")
            settings.setValue(setting[0], setting[1])


def process_command_line_args(args: list, settings: QSettings):
    debug = True if "DEBUG" in args else False
    settings.setValue("DEBUG", debug)

    remote = True if "REMOTE" in args else False
    settings.setValue("REMOTE", remote)
