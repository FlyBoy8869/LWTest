import os
from collections import namedtuple

from selenium import webdriver
import LWTest.web.interface.htmlelements as html

from LWTest.constants import dom

Credentials = namedtuple("Credentials", "user_name password")
# default credentials
_credentials = Credentials(
    user_name=os.getenv("LWTESTADMIN"),
    password=os.getenv("LWTESTADMINPASSWORD")
)

LoginFields = namedtuple("LoginFields", "user_name password submit_button")
# default login fields
_login_fields = LoginFields(
    user_name=html.HTMLTextInput(html.CSSXPath(dom.LOGIN_USERNAME_FIELD)),
    password=html.HTMLTextInput(html.CSSXPath(dom.LOGIN_PASSWORD_FIELD)),
    submit_button=html.HTMLButton(html.CSSXPath(dom.LOGIN_BUTTON))
)


class Login:
    def __init__(self, credentials: Credentials = _credentials, login_fields: LoginFields = _login_fields):
        self.__credentials = credentials
        self.__login_fields = login_fields

    def login(self, url: str, driver: webdriver.Chrome):
        driver.get(url)
        if "login" in driver.page_source.lower():
            self.__login_fields.user_name.fill(self.__credentials.user_name, driver)
            self.__login_fields.password.fill(self.__credentials.password, driver)
            self.__login_fields.submit_button.click(driver)
            driver.get(url)
