# spreadsheet.py
import datetime
import logging
import sys
from pathlib import Path
from typing import Tuple, Optional

import openpyxl
from openpyxl.workbook.workbook import Worksheet as openpyxlWorksheet, Workbook
from openpyxl.worksheet.worksheet import Worksheet

import LWTest.utilities.misc
import LWTest.utilities.time
from LWTest.spreadsheet import constants
from LWTest.utilities import returns

_CONVERSIONS = [float, float, float, int,
                float, float, float, int,
                float, float, float, str,
                str, str, lambda v: int(v) if type(v) == int else str(v), str, float, str]


def get_serial_numbers(path: str) -> Tuple[str]:
    """Loads serial numbers from a spreadsheet.
    Parameters
    ----------
    path: str
        spreadsheet_path to spreadsheet
    Returns
    -------
        tuple[str]
            a tuple of strings representing sensor serial numbers
    """

    return _extract_serial_numbers_from_worksheet(_get_worksheet_from_workbook(path))


def save_sensor_data(workbook_path, data_sets, temperature_reference: str) -> returns.Result:
    worksheet = _get_worksheet_from_workbook(workbook_path)

    for data_set in data_sets:
        for index, (location, reading) in enumerate(data_set):
            if not reading:
                continue

            if reading != 'NA':
                value = reading
                try:
                    value = _convert_reading_for_spreadsheet(reading, _CONVERSIONS[index])
                except Exception:
                    pass
                worksheet[location].value = value

    worksheet[constants.temperature_reference] = _convert_reading_for_spreadsheet(temperature_reference, float)
    worksheet[constants.tested_by].value = str("Charles Cognato")
    worksheet[constants.test_date].value = datetime.date.today()

    _save_workbook(workbook_path)

    return returns.Result(True, True)


def record_log_files_attached(workbook_path: str):
    worksheet = _get_worksheet_from_workbook(workbook_path)
    for cell in constants.LOG_FILE_CELLS:
        worksheet[cell] = str('Yes')

    _save_workbook(workbook_path)


def save_test_results(workbook_path: str, results: Tuple[str]):
    logger = logging.getLogger(__name__)

    logger.info(f"saving test results to spreadsheet: {results}")
    logger.info(f"using file: {workbook_path}")

    worksheet = _get_worksheet_from_workbook(workbook_path)
    logger.info(f"saving to worksheet {worksheet}")

    for result, location in zip(results, constants.FIVE_AMP_SAVE_LOCATIONS):
        logger.debug(f"saving '{result}' to location '{location}'")
        worksheet[location].value = str(result)

    _save_workbook(workbook_path)


# -------------------
# private interface -
# -------------------
_workbook: Optional[Workbook]


def _convert_reading_for_spreadsheet(reading, conversion):
    return conversion(LWTest.utilities.misc.normalize_reading(reading))


def _extract_serial_numbers_from_worksheet(worksheet: openpyxlWorksheet) -> Tuple[str]:
    logger = logging.getLogger(__name__)

    serial_numbers = [str(worksheet[serial_location].value) for serial_location in constants.SERIAL_LOCATIONS
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
    except RuntimeError:
        LWTest.utilities.misc.print_exception_info()
        raise RuntimeError


def _get_worksheet_from_workbook(path) -> openpyxlWorksheet:
    global _workbook
    logger = logging.getLogger(__name__)

    try:
        _open_workbook(path)
        worksheet = _workbook[constants.WORKSHEET_NAME]
        return worksheet
    except KeyError:
        logger.debug(f"Worksheet '{constants.WORKSHEET_NAME}' does not exist. Check the spelling in config.txt.")
        sys.exit(1)


def _save_workbook(path):
    _workbook.save(path)
    _close_workbook()


def _close_workbook():
    global _workbook

    if _workbook:
        _workbook.close()
        _workbook = None


class Spreadsheet:
    def __init__(self, path: Path, worksheet: Worksheet):
        self._path = path
        self._worksheet: Worksheet = worksheet

    def get_serial_numbers(self) -> list:
        raise NotImplementedError("Not yet.")

    def _extract_serial_numbers_from_worksheet(self, serial_locations: tuple) -> Tuple[str]:
        serial_numbers = [str(self._worksheet[serial_location].value) for serial_location in serial_locations
                          if str(self._worksheet[serial_location].value) != 'None']

        _close_workbook()

        return tuple(serial_numbers)
