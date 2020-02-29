from PyQt5.QtCore import QUrl, QSettings
from selenium import webdriver

from LWTest.constants import dom


_LOGIN_TEXT = "login"


class Credentials:
    def __init__(self, *, username: str, password: str):
        self._username = username
        self._password = password

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password


class PageAction:
    def do_action(self, driver: webdriver.Chrome):
        raise NotImplementedError("You must override this method.")


class ActionLogin(PageAction):
    def __init__(self, credentials: Credentials):
        self._credentials = credentials

    def do_action(self, driver: webdriver.Chrome):
        driver.find_element_by_xpath(dom.login_username_field).send_keys(self._credentials.username)
        driver.find_element_by_xpath(dom.login_password_field).send_keys(self._credentials.password)
        driver.find_element_by_xpath(dom.login_button).click()


class UrlLoader:
    def __init__(self, url: QUrl, driver: webdriver.Chrome, login_action: PageAction):
        assert url.url().startswith("http://192.168.2.1"), f"Invalid URL: {url.url()}."

        self._url = url
        self._driver: webdriver.Chrome = driver
        self._login_action = login_action

    @property
    def driver(self):
        return self._driver

    def load(self):
        self._driver.get(self._url.url())

        if self._login_required():
            self._login_action.do_action(self._driver)

    def _login_required(self) -> bool:
        return _LOGIN_TEXT in self._driver.page_source.lower()


if __name__ == '__main__':
    driver_location = "resources/drivers/chromedriver/windows/version_78-0-3904-70/chromedriver.exe"
    browser = webdriver.Chrome(executable_path=driver_location)
    loader = UrlLoader(QUrl("http://192.168.2.1/index.php/main/advanced_config"), browser,
                       ActionLogin(Credentials(username='administrator', password='FMIadm!n')))
    loader.load()
