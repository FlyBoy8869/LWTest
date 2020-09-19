from typing import Tuple

import shutil
import urllib.request
from pathlib import Path

import LWTest.utilities.returns as returns
from LWTest.constants import lwt


def download_log_files(path: Path) -> returns.Result:
    try:
        with urllib.request.urlopen(lwt.URL_LOG_FILES) as response, open(path.as_posix(), 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    except Exception as e:
        return returns.Result(False, None, str(e))

    return returns.Result(True, None)


def _create_serial_string(prefix: str, serial_numbers: Tuple[str, ...]) -> str:
    return "".join([prefix + serial_number for serial_number in serial_numbers])


def create_log_filename(path: str, serial_numbers: Tuple[str, ...]) -> Path:
    assert path, f"invalid path string '{path}'"

    spreadsheet_path = Path(path)
    return spreadsheet_path.parent / Path("logfiles" + _create_serial_string("-SN", serial_numbers) + ".zip")


def create_new_file_path(file_name: str, serial_numbers: Tuple[str, ...], base_name: str = "ATR-PRD#") -> Path:
    file_path = Path(file_name)

    new_name = base_name + _create_serial_string("-SN", serial_numbers)
    return file_path.parent / Path(new_name + file_path.suffix)


if __name__ == '__main__':
    # . filename = r"C:\Users\charles\Temp\ATR-PRD#-SN9800001-SN9800002-SN9800003-SN9800004-SN9800005-SN9800006.xlsm"
    # print(create_log_filename_from_spreadsheet_path(filename).as_posix())
    # print(create_log_filename_from_spreadsheet_path(filename).resolve())

    # . filename = "/Users/charles/tmp/ATR-PRD template file.xlsm"
    # print(create_new_file_name(filename, ("9800001", "9800002", "9800003")))

    serials = ("9800001", "9800002", "9800003")
    print(_create_serial_string("-SN", serials))
