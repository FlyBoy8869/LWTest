# utilities/misc.py
import logging
import sys
import traceback
from typing import List, Tuple

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


def print_exception_info():
    for line in traceback.format_exception(*sys.exc_info()):
        print(line.strip())


def normalize_reading(reading: str) -> str:
    return reading.replace(",", "")


def x_is_what_percent_of_y(dividend: int, divisor: int) -> float:
    assert divisor > 0, "divisor can not be less than 1"
    return dividend / divisor * 100
