import logging
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By

import LWTest.constants.lwt_constants as lwt_const
from LWTest.collector.state.reachable import PageReachable

_DATE_AND_TIME_ELEMENT = "//*[@id='maindiv']/div[2]"
_DATE_AND_TIME_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[1]"
_ADMIN_PASSWORD_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[2]"
_UPDATE_BUTTON = "//*[@id='maindiv']/form/input[3]"


class DateTimeSynchronizer:
    """Ensures the collector date and time is within 1 minute of the current date and time."""
    DELTA_THRESHOLD: float = 2.0

    def __init__(self, url: str, password: str):
        self._logger = logging.getLogger(__name__)
        self._url = url
        self._password = password

    def sync_date_time(self, driver: webdriver.Chrome):
        self._logger.info("checking collector date and time")
        driver.get(self._url)
        time_delta = self.calculate_delta_in_minutes(
            datetime.now(), self._get_collector_date(driver)
        )

        if time_delta > self.DELTA_THRESHOLD:
            date = self._set_date(self._password, driver)
            self._logger.debug(f"setting date to {date}")
            return date

        return None

    @staticmethod
    def _set_date(password: str, driver: webdriver.Chrome) -> str:
        current_date_time_str = DateTimeSynchronizer.get_current_date_string()

        driver.find_element(by=By.XPATH, value=_DATE_AND_TIME_INPUT_ELEMENT).send_keys(current_date_time_str)
        driver.find_element(by=By.XPATH, value=_ADMIN_PASSWORD_INPUT_ELEMENT).send_keys(password)
        driver.find_element(by=By.XPATH, value=_UPDATE_BUTTON).click()

        return current_date_time_str

    @staticmethod
    def get_current_date_string() -> str:
        now = datetime.now()
        return f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"

    @staticmethod
    def calculate_delta_in_minutes(time_1: datetime, time_2: datetime) -> float:
        """Returns the difference of time_1 - time_2 in minutes."""
        # Don't change this formula. It accounts for the possible difference
        # of exact days i.e., where days is >= 1 and the hours, minutes and seconds = 0, without
        # having to check the other attributes of the timedelta object.
        return (time_1 - time_2) / timedelta(minutes=1)

    @staticmethod
    def _get_collector_date(driver: webdriver.Chrome) -> datetime:
        element = driver.find_element(by=By.XPATH, value=_DATE_AND_TIME_ELEMENT)
        return datetime.strptime(element.get_attribute("textContent").split('\n', 1)[0], "%c")


class Power:
    URL: str = lwt_const.URL_DATE_TIME

    def __init__(self):
        self.checker = PageReachable(self.URL)

    @property
    def is_on(self) -> bool:
        return self.checker.try_to_load() == PageReachable.REACHED

    @property
    def is_off(self) -> bool:
        return not self.is_on
