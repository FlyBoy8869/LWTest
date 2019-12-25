# utilities/utilities.py
import os
import sys
import traceback
from time import sleep

from PyQt5.QtCore import QSettings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from LWTest.config.dom import constants as dom


def print_exception_info():
    for line in traceback.format_exception(*sys.exc_info()):
        print(line.strip())


def to_bool(value) -> bool:
    """Converts any variation the strings 'true' and 'false' to boolean values."""

    # explicit cast is for protection
    if str(value).lower() == "true":
        return True
    else:
        return False


def indicator():
    # characters = ['\u25D4', '\u25D1', '\u25D5', '\u25CF']
    characters = ['\u259A', '\u259E']
    index = 0

    while True:
        yield characters[index]
        index += 1
        if index > 1:
            index = 0


def page_failed_to_load(browser: webdriver.Chrome, path_to_element):
    try:
        browser.find_element_by_xpath(path_to_element)
    except NoSuchElementException:
        return True

    return False


def load_start_page(browser: webdriver.Chrome):
    browser.get("file://" + os.path.abspath('LWTest/resources/startup/start_page.html'))


def get_page_login_if_needed(url: str, browser: webdriver.Chrome):
    settings = QSettings()
    user = settings.value("main/admin_user")
    password = settings.value("main/admin_password")

    browser.get(url)
    try:
        # If we end up on the login page.
        browser.find_element_by_xpath(dom.login_header)
        browser.find_element_by_xpath(dom.login_username_field).send_keys(user)
        browser.find_element_by_xpath(dom.login_password_field).send_keys(password)
        browser.find_element_by_xpath(dom.login_button).click()
    except NoSuchElementException:
        pass
    finally:
        sleep(2)
        browser.get(url)
