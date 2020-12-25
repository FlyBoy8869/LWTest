import logging
from datetime import datetime, timedelta

from selenium import webdriver

_DATE_AND_TIME_ELEMENT = "//*[@id='maindiv']/div[2]"
_DATE_AND_TIME_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[1]"
_ADMIN_PASSWORD_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[2]"
_UPDATE_BUTTON = "//*[@id='maindiv']/form/input[3]"


class DateVerifier:
    """Ensures the collector date and time is within 1 minute of the current date and time."""
    def __init__(self, url: str, password: str):
        self._logger = logging.getLogger(__name__)
        self._url = url
        self._password = password

    def sync_data_time(self, driver: webdriver.Chrome):
        driver.get(self._url)
        time_delta = self._get_delta_in_minutes(
            datetime.now(), self._get_collector_date(driver, self._logger),
            self._logger
        )

        if time_delta > 1.0:
            self._set_date(self._password, driver, self._logger)

    @staticmethod
    def _set_date(password: str, driver: webdriver.Chrome, logger):
        now = datetime.now()
        current_date_time_str = \
            f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"
        logger.debug(f"setting date to {current_date_time_str}")

        driver.find_element_by_xpath(_DATE_AND_TIME_INPUT_ELEMENT).send_keys(
            current_date_time_str
        )
        driver.find_element_by_xpath(_ADMIN_PASSWORD_INPUT_ELEMENT).send_keys(password)
        driver.find_element_by_xpath(_UPDATE_BUTTON).click()

    @staticmethod
    def _get_delta_in_minutes(now: datetime, collector_date: datetime, logger) -> float:
        delta = (now - collector_date) / timedelta(minutes=1)
        logger.debug(f"time delta = {delta}")
        return delta

    @staticmethod
    def _get_collector_date(driver: webdriver.Chrome, logger) -> datetime:
        element = driver.find_element_by_xpath(_DATE_AND_TIME_ELEMENT)
        date_time = datetime.strptime(element.get_attribute("textContent").split('\n', 1)[0], "%c")
        logger.debug(f"date and time read from the collector = {date_time}")
        return date_time
