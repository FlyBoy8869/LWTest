from selenium import webdriver


class Credentials:
    def __init__(self, *, user_name: str, password: str):
        self._user_name = user_name
        self._password = password

    @property
    def user_name(self):
        return self._user_name

    @property
    def password(self):
        return self._password


class LoginFields:
    def __init__(self, *, user_name: str, password: str, submit_button: str):
        self._user_name_field = user_name
        self._password_field = password
        self._submit_button = submit_button

    def fill(self, user_name: str, password: str, driver: webdriver.Chrome):
        user_name_field = driver.find_element_by_xpath(self._user_name_field)
        user_name_field.clear()
        user_name_field.send_keys(user_name)

        password_field = driver.find_element_by_xpath(self._password_field)
        password_field.clear()
        password_field.send_keys(password)

    def click_submit(self, driver: webdriver.Chrome):
        driver.find_element_by_xpath(self._submit_button).click()


class Login:
    def __init__(self, credentials: Credentials, login_fields: LoginFields):
        self._credentials = credentials
        self._login_fields = login_fields

    def login(self, driver: webdriver.Chrome):
        self._login_fields.fill(self._credentials.user_name, self._credentials.password, driver)
        self._login_fields.click_submit(driver)
