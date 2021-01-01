# logging.py
import logging

from PyQt5.QtCore import QSettings


def _get_logging_level_constant(level: str):
    level_constants = {"debug": logging.DEBUG,
                       "info": logging.INFO,
                       "warning": logging.WARNING,
                       "error": logging.ERROR,
                       "critical": logging.CRITICAL}

    return level_constants.get(level, logging.WARNING)


def initialize():
    settings = QSettings()
    level = settings.value('main/debug_level')
    print(f"log level from config.txt: {level}")
    if level is None:
        return

    console_handler = logging.StreamHandler()  # defaults to sys.stderr
    console_handler.addFilter(lambda r: False if "selenium" in r.name else True)
    console_handler.addFilter(lambda r: False if "urllib3" in r.name else True)
    console_handler.addFilter(lambda r: False if "test _log" in r.name else True)

    file_handler = logging.FileHandler('app.log', mode='w')
    file_handler.addFilter(lambda r: False if "selenium" in r.name else True)
    file_handler.addFilter(lambda r: False if "urllib3" in r.name else True)
    file_handler.addFilter(lambda r: False if "test _log" in r.name else True)

    logging_format = [
        "%(levelname)s: ",
        "%(asctime)s : ",
        "%(name)s : ",
        "%(module)s.",
        "%(funcName)s(), ",
        "Line %(lineno)d - ",
        "%(message)s",
    ]

    # noinspection PyArgumentList
    logging.basicConfig(
        level=_get_logging_level_constant(level),
        format="".join(logging_format),
        handlers=[console_handler, file_handler]
    )
