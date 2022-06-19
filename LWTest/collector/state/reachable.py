import logging

import requests
from PyQt6.QtCore import QObject


class PageReachable(QObject):
    REACHED: bool = True
    UNREACHABLE: bool = False

    TIMEOUT = 10

    def __init__(self, url: str):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._url: str = url

    def try_to_load(self):
        msg = f"collector failed to serve: '{self._url}'"
        try:
            if 200 == requests.get(self._url, timeout=self.TIMEOUT).status_code:
                return self.REACHED
        except requests.exceptions.RequestException:
            msg = f"unable to reach collector: {self._url}"

        self._logger.debug(msg)
        return self.UNREACHABLE
