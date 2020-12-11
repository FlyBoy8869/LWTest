import logging
import os
from collections import namedtuple

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

import LWTest.web.interface.htmlelements as html
from LWTest.constants import dom

_LOGIN_USERNAME_FIELD = '//*[@id="username"]'
_LOGIN_PASSWORD_FIELD = '//*[@id="password"]'
_LOGIN_BUTTON = '/html/body/div/div/form/p[3]/input'

Credentials = namedtuple("Credentials", "user_name password")
_credentials = Credentials(
    user_name=os.getenv("LWTESTADMIN"),
    password=os.getenv("LWTESTADMINPASSWORD")
)

LoginFields = namedtuple("LoginFields", "user_name password submit_button")
_login_fields = LoginFields(
    user_name=html.HTMLTextInput(html.CSSXPath(_LOGIN_USERNAME_FIELD)),
    password=html.HTMLTextInput(html.CSSXPath(_LOGIN_PASSWORD_FIELD)),
    submit_button=html.HTMLButton(html.CSSXPath(_LOGIN_BUTTON))
)


class _Login:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)
        self.__credentials = _credentials
        self.__login_fields = _login_fields
        self.__logger.debug("created instance of Login class")

    def login(self, driver: webdriver.Chrome):
        self.__login_fields.user_name.fill(self.__credentials.user_name, driver)
        self.__login_fields.password.fill(self.__credentials.password, driver)
        self.__login_fields.submit_button.click(driver)
        self.__logger.debug("logged in")


class Page:
    """Uses Chromedriver to retrieve a page and logs in if necessary."""
    SUCCESS = 0
    NETWORK_ERROR = -1
    SERVER_ERROR = -2

    _logger_inner = _Login()

    @staticmethod
    def get(url: str, driver: webdriver.Chrome):
        logger = logging.getLogger(__name__)

        try:
            driver.get(url)
        except WebDriverException as exc:
            # this exception appears to be raised only when the webserver is not running
            logger.exception(exc)
            return Page.NETWORK_ERROR

        # the reload button shows up when Google Chrome has an issue finding the page
        # but selenium doesn't raise WebDriverException
        #
        # it is possible that this only occurs when making requests to
        # my webapp mockcollector because it is not providing the same
        # response or behavior that Google Chrome is providing
        if driver.find_elements_by_css_selector("#reload-button"):
            logger.debug(f"Chromedriver encountered an error loading page '{url}'")
            return Page.SERVER_ERROR

        if "login" in driver.page_source.lower():
            Page._login(driver)
            driver.get(url)

        return Page.SUCCESS

    @staticmethod
    def _login(driver):
        Page._logger_inner.login(driver)


class Submit:
    @classmethod
    def create_submit_button_for_phase_angle(cls, password: str):
        password_field = html.HTMLTextInput(html.CSSXPath(dom.configuration_password))
        submit_selector = html.HTMLButton(html.CSSXPath(dom.configuration_save_changes))
        return cls(password, password_field, submit_selector)

    @classmethod
    def create_submit_button_for_temperature_config(cls, password: str):
        password_field = html.HTMLTextInput(html.CSSXPath(dom.temperature_password))
        submit_selector = html.HTMLButton(html.CSSXPath(dom.temperature_submit_button))
        return cls(password, password_field, submit_selector)

    @classmethod
    def create_submit_button_for_raw_config(cls, password: str):
        password_field = html.HTMLTextInput(html.CSSXPath(dom.raw_config_password))
        submit_selector = html.HTMLButton(html.CSSXPath(dom.raw_config_submit_button))
        return cls(password, password_field, submit_selector)

    @classmethod
    def create_submit_button_for_voltage_ride_through(cls, password: str):
        password_field = html.HTMLTextInput(html.CSSXPath(dom.vrt_admin_password_field))
        submit_selector = html.HTMLButton(html.CSSXPath(dom.vrt_save_configuration_button))
        return cls(password, password_field, submit_selector)

    def __init__(self, password: str, password_field: html.HTMLTextInput, submit_selector: html.HTMLButton):
        self._password = password
        self._password_field = password_field
        self._submit_selector = submit_selector

    def click(self, driver: webdriver.Chrome):
        self._password_field.fill(self._password, driver)
        self._submit_selector.click(driver)
