# spreadsheet.py
import datetime
import logging
import sys
from typing import Tuple

import openpyxl
from PyQt5.QtCore import QSettings
from openpyxl.workbook.workbook import Worksheet as openpyxlWorksheet

import LWTest.utilities.misc
import LWTest.utilities.time
from LWTest.spreadsheet import constants

_CONVERSIONS = [float, float, float, int,
                float, float, float, int,
                float, float, float, str,
                str, str, lambda v: int(v) if type(v) == int else str(v), str, float, str]

_SERIAL_LOCATIONS = QSettings().value('spreadsheet/serial_locations').split(' ')
_FIVE_AMP_SAVE_LOCATIONS = QSettings().value('spreadsheet/result_locations').split(' ')
_WORKSHEET_NAME = QSettings().value("spreadsheet/worksheet")


def get_serial_numbers(path: str) -> Tuple[str]:
    """Loads serial numbers from a spreadsheet.
    Parameters
    ----------
    path: str
        path to spreadsheet
    Returns
    -------
        tuple[str]
            a tuple of strings representing sensor serial numbers
    """

    return _extract_serial_numbers_from_worksheet(_get_worksheet_from_workbook(path))


def save_sensor_data(workbook_path, data_sets, temperature_reference: str):
    worksheet = _get_worksheet_from_workbook(workbook_path)

    for data_set in data_sets:
        for index, (location, reading) in enumerate(data_set):
            if not reading:
                continue

            if reading != 'NA':
                value = _convert_reading_for_spreadsheet(reading, _CONVERSIONS[index])
                worksheet[location].value = value

    worksheet[constants.temperature_reference] = _convert_reading_for_spreadsheet(temperature_reference, float)
    worksheet[constants.tested_by].value = str("Charles Cognato")
    worksheet[constants.test_date].value = datetime.date.today()

    _save_workbook(workbook_path)


def save_test_results(workbook_path: str, results: Tuple[str]):
    logger = logging.getLogger(__name__)

    logger.info(f"saving test results to spreadsheet: {results}")
    logger.info(f"using file: {workbook_path}")

    worksheet = _get_worksheet_from_workbook(workbook_path)
    logger.info(f"saving to worksheet {worksheet}")

    for result, location in zip(results, _FIVE_AMP_SAVE_LOCATIONS):
        logger.debug(f"saving '{result}' to location '{location}'")
        worksheet[location].value = str(result)

    _save_workbook(workbook_path)


# -------------------
# private interface -
# -------------------
_workbook = None


def _convert_reading_for_spreadsheet(reading, conversion):
    return conversion(reading)


def _extract_serial_numbers_from_worksheet(worksheet: openpyxlWorksheet) -> Tuple[str]:
    logger = logging.getLogger(__name__)

    serial_numbers = [str(worksheet[serial_location].value) for serial_location in _SERIAL_LOCATIONS
                      if str(worksheet[serial_location].value) != 'None']

    _close_workbook()

    logger.debug(f"Extracted serial numbers: {serial_numbers}")

    return tuple(serial_numbers)


def _open_workbook(filename: str):
    global _workbook
    logger = logging.getLogger(__name__)

    try:
        # read_only=False, keep_vba=True prevent Excel from thinking the spreadsheet has been corrupted
        _workbook = openpyxl.load_workbook(filename=filename, read_only=False, keep_vba=True)
    except FileNotFoundError:
        logger.debug("spreadsheet not found")
        LWTest.utilities.misc.print_exception_info()
        sys.exit(1)
    except Exception:
        LWTest.utilities.misc.print_exception_info()
        raise Exception


def _get_worksheet_from_workbook(path) -> openpyxlWorksheet:
    global _workbook
    logger = logging.getLogger(__name__)

    try:
        _open_workbook(path)
        worksheet = _workbook[_WORKSHEET_NAME]
        return worksheet
    except KeyError:
        logger.debug(f"Worksheet '{_WORKSHEET_NAME}' does not exist. Check the spelling in config.txt.")
        sys.exit(1)


def _save_workbook(path):
    _workbook.save(path)
    _close_workbook()


def _close_workbook():
    global _workbook

    _workbook.close()
    _workbook = None
