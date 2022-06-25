# spreadsheet.py
import contextlib
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


def rssi_conversion(value: str):
    try:
        return int(value)
    except ValueError:
        return value


_CONVERSIONS = [float, float, float, int,
                float, float, float, int,
                float, float, float, str,
                str, str, rssi_conversion, str, float, str]


def create_test_record(serial_numbers, path: str):
    _enter_serial_numbers_in_worksheet(serial_numbers, _get_worksheet_from_workbook(path), path)


def get_serial_numbers(path: str) -> Tuple[str]:
    """Load serial numbers from a spreadsheet.

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


def save_test_results(path, data_sets, references) -> returns.Result:
    worksheet = _get_worksheet_from_workbook(path)
    temperature_reference, high_references, low_references = references

    _save_reference_data(worksheet, temperature_reference, high_references, low_references)
    _save_test_data(data_sets, worksheet)
    _save_admin_data(worksheet)
    _protect_worksheet(worksheet)
    _save_workbook(path)

    return returns.Result(True, True)


def record_log_files_attached(workbook_path: str):
    worksheet = _get_worksheet_from_workbook(workbook_path)
    for cell in constants.LOG_FILE_CELLS:
        worksheet[cell] = str('Yes')

    _save_workbook(workbook_path)


# -------------------
# private interface -
# -------------------
_workbook: Optional[Workbook] = None


def _convert_reading_for_spreadsheet(reading, conversion):
    with contextlib.suppress(ValueError):
        return conversion(LWTest.utilities.misc.normalize_reading(reading))


def _enter_serial_numbers_in_worksheet(serial_numbers, worksheet: openpyxlWorksheet, path: str):
    for index, serial_number in enumerate(serial_numbers):
        worksheet[constants.SERIAL_LOCATIONS[index]].value = int(serial_numbers[index])

    _save_workbook(path)
    _close_workbook()


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
    except RuntimeError as e:
        LWTest.utilities.misc.print_exception_info()
        raise RuntimeError from e


def _get_worksheet_from_workbook(path) -> openpyxlWorksheet:
    global _workbook
    logger = logging.getLogger(__name__)

    try:
        _open_workbook(path)
        return _workbook[constants.WORKSHEET_NAME]
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


def _protect_worksheet(worksheet):
    # Attention: Not working on macOS. Haven't tried Windows yet.
    #  Could have something to do with meta-data not being saved.
    worksheet.protection.sheet = True
    worksheet.protection.enable()
    worksheet.protection.password = "12345"


def _save_admin_data(worksheet):
    worksheet[constants.tested_by].value = str("Charles Cognato")
    worksheet[constants.test_date].value = datetime.date.today()


def _save_reference_data(worksheet, temperature_reference, high_references, low_references):
    conversions = [float, float, float, int]

    def _save_data(refs, cells_):
        for i, r in enumerate(refs):
            _save_data_to_cell(_convert_reading_for_spreadsheet(r, conversions[i]), cells_[i], worksheet)

    _save_data_to_cell(
        _convert_reading_for_spreadsheet(temperature_reference, float),
        constants.temperature_reference,
        worksheet
    )

    for reference_values, cells in \
            ((high_references, constants.high_reference_cells), (low_references, constants.low_reference_cells)):
        if reference_values:
            for values, data_cells in [(reference_values, cells)]:
                _save_data(values, data_cells)


def _save_test_data(data_sets, worksheet):
    for data_set in data_sets:
        for index, (location, reading) in enumerate(data_set):
            if not reading or reading == 'NA':
                continue

            _save_data_to_cell(
                _convert_reading_for_spreadsheet(reading, _CONVERSIONS[index]),
                location,
                worksheet
            )


def _save_data_to_cell(data, cell, worksheet) -> None:
    worksheet[cell].value = data
