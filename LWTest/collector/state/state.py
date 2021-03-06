import logging
from datetime import datetime, timedelta

from selenium import webdriver

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
        time_delta = self._get_delta_in_minutes(
            datetime.now(), self._get_collector_date(driver, self._logger), self._logger
        )

        if time_delta > self.DELTA_THRESHOLD:
            return self._set_date(self._password, driver, self._logger)

        return None

    @staticmethod
    def _set_date(password: str, driver: webdriver.Chrome, logger) -> str:
        logger.info("updating collector date and time")
        now = datetime.now()
        current_date_time_str = \
            f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"
        logger.debug(f"setting date to {current_date_time_str}")

        driver.find_element_by_xpath(_DATE_AND_TIME_INPUT_ELEMENT).send_keys(
            current_date_time_str
        )
        driver.find_element_by_xpath(_ADMIN_PASSWORD_INPUT_ELEMENT).send_keys(password)
        driver.find_element_by_xpath(_UPDATE_BUTTON).click()

        return current_date_time_str

    @staticmethod
    def _get_delta_in_minutes(time_1: datetime, time_2: datetime, logger) -> float:
        """Returns the difference of time_1 - time_2 in minutes."""
        # Don't change this formula. It accounts for the possible difference
        # of exact days i.e., where days is >= 1 and the hours, minutes and seconds = 0, without
        # having to check the other attributes of the timedelta object.
        delta = (time_1 - time_2) / timedelta(minutes=1)
        logger.debug(f"time delta = {delta}")
        return delta

    @staticmethod
    def _get_collector_date(driver: webdriver.Chrome, logger) -> datetime:
        element = driver.find_element_by_xpath(_DATE_AND_TIME_ELEMENT)
        date_time = datetime.strptime(element.get_attribute("textContent").split('\n', 1)[0], "%c")
        logger.debug(f"date and time read from the collector = {date_time}")
        return date_time


class Power:
    URL: str = lwt_const.URL_DATE_TIME
    ON: bool = True
    OFF: bool = False

    def __init__(self):
        self.checker = PageReachable(self.URL)

    @property
    def is_on(self):
        return self.ON if self.checker.try_to_load() == PageReachable.REACHED else self.OFF

    @property
    def is_off(self):
        return not self.is_on
