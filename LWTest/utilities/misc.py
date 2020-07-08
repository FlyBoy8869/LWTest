# utilities/misc.py
import os
import re
from typing import List, Tuple, Optional

import sys
import traceback

from PyQt5.QtCore import QSettings
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

import LWTest.constants.LWTConstants as LWT
from LWTest.constants import dom as dom


def ensure_six_numbers(serial_numbers: List[str]) -> Tuple[str]:
    """
    Pads a list to ensure it contains exactally six elements.

    :param serial_numbers: Sequence of strings representing sensor serial numbers.

    :return: A tuple containing exactly 6 numbers.

    >>> ensure_six_numbers(["1", "2", "3", "4", "5", "6", "7"])
    Traceback (most recent call last):
        ...
    AssertionError: Only six serial numbers allowed.

    >>> ensure_six_numbers(["1"])
    ('1', '0', '0', '0', '0', '0')
    """

    assert len(serial_numbers) <= 6, "Only six serial numbers allowed."

    numbers: List[str] = serial_numbers[:]
    numbers.extend(['0'] * (6 - len(numbers)))

    assert len(numbers) == 6, "return value must contain exactly six numbers"

    return tuple(numbers)


def get_page_login_if_needed(url: str, browser: webdriver.Chrome, text=""):
    settings = QSettings()
    max_retries: int = 2
    retries = 0
    user = settings.value("main/admin_user")
    password = settings.value("main/admin_password")

    while retries < max_retries:
        print(f"{__name__}.get_page_login_if_needed: about to load page")
        browser.get(url)
        print(f"{__name__}.get_page_login_if_needed: loaded page")

        if text not in browser.page_source:
            print(f"{__name__}.get_page_login_if_needed: text not on page, attempting login")
            try:
                # _driver.get(_url)
                browser.find_element_by_xpath(dom.login_header)
                browser.find_element_by_xpath(dom.login_username_field).send_keys(user)
                browser.find_element_by_xpath(dom.login_password_field).send_keys(password)
                browser.find_element_by_xpath(dom.login_button).click()

                if text in browser.page_source:
                    print(f"{__name__}.get_page_login_if_needed: navigation successful")
                    break
            except NoSuchElementException:
                print(f"{__name__}.get_page_login_if_needed: received a 'NoSuchElementException'")

        retries += 1


def indicator():
    characters = ['\u259A', '\u259E']
    index = 0

    while True:
        yield characters[index]
        index += 1
        if index > 1:
            index = 0


def load_start_page(browser: webdriver.Chrome):
    browser.get("file://" + os.path.abspath('LWTest/resources/startup/start_page.html'))


def page_failed_to_load(browser: webdriver.Chrome, path_to_element):
    try:
        browser.find_element_by_xpath(path_to_element)
    except NoSuchElementException:
        return True

    return False


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


def normalize_reading(reading: str) -> str:
    return reading.replace(",", "")


def x_is_what_percent_of_y(dividend: int, divisor: int) -> Optional[float]:
    assert divisor > 0, "divisor can not be less than 1"
    return dividend / divisor * 100


def filter_out_na(readings: list) -> list:
    return list(filter(lambda r: r != LWT.NO_DATA, readings))


serial_number_pattern = re.compile(r"\s*\d{7}")


def line_starts_with_serial_number(line: str):
    return serial_number_pattern.match(line)


if __name__ == '__main__':
    import doctest

    count, _ = doctest.testmod()
    if count == 0:
        print("All tests passed.")
