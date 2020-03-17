import sys
from datetime import datetime, timedelta

from PyQt5.QtCore import QUrl, QSettings
from selenium import webdriver


_DATE_AND_TIME_ELEMENT = "//*[@id='maindiv']/div[2]"
_DATE_AND_TIME_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[1]"
_ADMIN_PASSWORD_INPUT_ELEMENT = "//*[@id='maindiv']/form/input[2]"
_UPDATE_BUTTON = "//*[@id='maindiv']/form/input[3]"


class DateVerifier:
    """Compares the Collector's date and time to the current date and time
    and sets the collector to the current date and time if the difference is greater than one minute."""
    def __init__(self, url: QUrl, password: str):
        self._url: QUrl = url
        self._password = password

    def verify_date(self, driver: webdriver.Chrome):
        driver.get(self._url.url())
        time_delta = self._get_delta_in_minutes(datetime.now(), self._get_collector_date(driver))

        if time_delta > 1.0:
            self._set_date(driver)

    def _set_date(self, driver: webdriver.Chrome):
        now = datetime.now()
        driver.find_element_by_xpath(_DATE_AND_TIME_INPUT_ELEMENT).send_keys(
            f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}"
        )

        driver.find_element_by_xpath(_ADMIN_PASSWORD_INPUT_ELEMENT).send_keys(self._password)

        driver.find_element_by_xpath(_UPDATE_BUTTON).click()

    def _get_delta_in_minutes(self, now: datetime, collector_date: datetime) -> float:
        return (now - collector_date) / timedelta(minutes=1)

    def _get_collector_date(self, driver: webdriver.Chrome) -> datetime:
        return datetime.strptime(
            driver.find_element_by_xpath(_DATE_AND_TIME_ELEMENT).get_attribute("textContent").split('\n', 1)[0],
            "%c")


if __name__ == '__main__':
    driver = webdriver.Chrome(
        executable_path="../resources/drivers/chromedriver/windows/version_80_0_3987_106/chromedriver.exe")
    # driver.get("http://192.168.2.1/index.php/upgrade/date_and_time")
    # if "LineWatch" in driver.title:
    #     print("Retrieved page successfully.")
    # else:
    #     print("Unable to load page.")
    #     sys.exit(1)

    # todays_date = datetime.now()
    # collector_date = datetime.strptime(
    #     driver.find_element_by_xpath(_DATE_AND_TIME_ELEMENT).get_attribute("textContent").split('\n', 1)[0],
    #     '%c')
    # print(f"Today's date: {todays_date}")
    # print(f"Collector date: {collector_date}")
    #
    # time_delta = todays_date - collector_date
    # print(f"time delta: {time_delta}")
    #
    # total_minutes = time_delta / timedelta(minutes=1)
    # print(f"total minutes: {total_minutes}")
    #
    # if total_minutes > 1.0:
    #     print("Collector time is out of required tolerance.")
    # else:
    #     print("Collector time is good.")

    dv = DateVerifier(QUrl("http://192.168.2.1/index.php/upgrade/date_and_time"), "Q854Xj8X")
    dv.verify_date(driver)

    driver.quit()
