# utilities/misc.py
import logging
import traceback

import os
import sys
from PyQt5.QtCore import QSettings
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from typing import List, Tuple, Optional

from LWTest.constants import dom, lwt


_logger = logging.getLogger(__name__)


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


def get_page_login_if_needed(url: str, browser: webdriver.Chrome):
    _logger.debug(f"requesting {url}, checking if login is required")

    settings = QSettings()
    user = settings.value("main/admin_user")
    password = settings.value("main/admin_password")

    try:
        browser.get(url)
    except WebDriverException:
        return

    if "login" in browser.page_source.lower():
        _logger.debug("logging in")

        browser.find_element_by_xpath(dom.login_username_field).send_keys(user)
        browser.find_element_by_xpath(dom.login_password_field).send_keys(password)
        browser.find_element_by_xpath(dom.login_button).click()

        browser.get(url)


def print_exception_info():
    for line in traceback.format_exception(*sys.exc_info()):
        print(line.strip())


def normalize_reading(reading: str) -> str:
    return reading.replace(",", "")


def x_is_what_percent_of_y(dividend: int, divisor: int) -> Optional[float]:
    assert divisor > 0, "divisor can not be less than 1"
    return dividend / divisor * 100


def filter_out_na(readings: list) -> list:
    return list(filter(lambda r: r != lwt.NO_DATA, readings))


if __name__ == '__main__':
    import doctest

    count, _ = doctest.testmod()
    if count == 0:
        print("All tests passed.")
