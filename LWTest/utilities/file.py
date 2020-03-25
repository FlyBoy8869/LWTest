import urllib.request
import shutil
from pathlib import Path
from time import sleep

import LWTest.LWTConstants as LWT_constants
import LWTest.utilities.returns as returns


_LOG_FILE_URL = 'http://192.168.2.1/downloadLogs.php'


if LWT_constants.TESTING:
    def download_log_files(path: Path) -> returns.Result:
        import random

        sleep(1)

        if random.choice([True, False]):
            return returns.Result(success=True, value=None)
        else:
            return returns.Result(success=False, value=None, error="Bad shit happened.")
else:
    def download_log_files(path: Path) -> returns.Result:
        try:
            with urllib.request.urlopen(_LOG_FILE_URL) as response, open(path.as_posix(), 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            return returns.Result(False, None, str(e))

        return returns.Result(True, None)


def create_log_filename_from_spreadsheet_path(path: str) -> Path:
    assert path, f"invalid path string '{path}'"

    spreadsheet_path = Path(path)
    spreadsheet_path_parts = spreadsheet_path.parts
    serial_numbers = spreadsheet_path_parts[-1].split("#", 1)[-1].split(".", 1)[0]
    log_file_path = Path(spreadsheet_path.parent.as_posix() + "/logfiles" + serial_numbers + ".zip")

    return log_file_path


if __name__ == '__main__':
    filename = r"C:\Users\charles\Temp\ATR-PRD#-SN9800001-SN9800002-SN9800003-SN9800004-SN9800005-SN9800006.xlsm"
    print(create_log_filename_from_spreadsheet_path(filename).as_posix())
