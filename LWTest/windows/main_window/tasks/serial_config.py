from functools import partial

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMessageBox
from selenium import webdriver

from LWTest.workers.serial_config_worker import SerialConfigWorker


_load_failure = None


def configure_serial_numbers(serial_numbers: tuple, browser: webdriver.Chrome,
                             parent, thread_pool, link_checker):
    settings = QSettings()

    config_worker = SerialConfigWorker(serial_numbers,
                                       settings.value("main/config_password"),
                                       browser,
                                       settings.value("pages/configuration"))
    # config_worker.signals.configured_serial_numbers.connect(self._determine_link_status)

    global _load_failure
    _load_failure = partial(_serial_config_page_failed_to_load, parent, thread_pool, browser)

    config_worker.signals.configured_serial_numbers.connect(link_checker)
    config_worker.signals.serial_config_page_failed_to_load.connect(_load_failure)

    thread_pool.start(config_worker)


def _serial_config_page_failed_to_load(parent, thread_pool, browser, url: str, serial_numbers: tuple):
    button = QMessageBox.warning(parent, "LWTest - Page Load Error", f"Failed to load {url}\n\n" +
                                 "Check the collector and click 'Ok' to retry.",
                                 QMessageBox.Ok | QMessageBox.Cancel)

    if button == QMessageBox.Ok:
        print("retrying to config the collector")
        configure_serial_numbers(serial_numbers, browser, parent, thread_pool)
