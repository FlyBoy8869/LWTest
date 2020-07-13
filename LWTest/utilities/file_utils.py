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


def create_log_filename_from_spreadsheet_path(path: str) -> Path:
    """Convert a LineWatch results spreadsheet path into a path for saving the log file.

    For example,

    /Users/charles/Desktop/ATR-PRD#-SN9802386-SN9802165-SN9802316-SN9802334-SN9802310-SN9802193.xlsm

        turns into

    /Users/charles/Temp/logfiles-SN9800001-SN9800002-SN9800003-SN9800004-SN9800005-SN9800006.zip
    """
    def get_file_name(path_: Path) -> str:
        return path_.parts[-1]

    def get_serial_numbers(text: str) -> str:
        return text.split("#", 1)[-1]

    def lose_extension(file_name: str) -> str:
        return file_name.split(".")[0]

    assert path, f"invalid path string '{path}'"

    spreadsheet_path = Path(path)
    serial_numbers = get_serial_numbers(lose_extension(get_file_name(spreadsheet_path)))
    log_file_path = spreadsheet_path.parent / Path("logfiles" + serial_numbers + ".zip")

    return log_file_path


if __name__ == '__main__':
    filename = r"C:\Users\charles\Temp\ATR-PRD#-SN9800001-SN9800002-SN9800003-SN9800004-SN9800005-SN9800006.xlsm"
    print(create_log_filename_from_spreadsheet_path(filename).as_posix())
    print(create_log_filename_from_spreadsheet_path(filename).resolve())
