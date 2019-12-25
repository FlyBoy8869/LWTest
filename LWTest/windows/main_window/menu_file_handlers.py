from PyQt5.QtCore import QSettings

from LWTest.workers.upgrade_worker import UpgradeWorker


def menu_file_save_handler():
    print("saving data")


def menu_file_upgrade_handler(serial_number: str):
    settings = QSettings()
    upgrade_worker = UpgradeWorker(serial_number, settings.value("pages/software_upgrade"))
