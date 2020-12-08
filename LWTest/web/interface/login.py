from collections import namedtuple

from selenium import webdriver
import LWTest.web.interface.htmlelements as html


Credentials = namedtuple("Credentials", "user_name password")
LoginFields = namedtuple("LoginFields", "user_name password submit_button")


class Login:
    @classmethod
    def create_from_strings(cls,url: str, user: str, password: str, user_field: str, password_field: str, submit_button: str):
        credentials = Credentials(user_name=user, password=password)
        login_fields = LoginFields(
            user_name=html.HTMLTextInput(html.CSSXPath(user_field)),
            password=html.HTMLTextInput(html.CSSXPath(password_field)),
            submit_button=html.HTMLButton(html.CSSXPath(submit_button))
        )
        return cls(url, credentials, login_fields)

    def __init__(self, url: str, credentials: Credentials, login_fields: LoginFields):
        self.__url = url
        self.__credentials = credentials
        self.__login_fields = login_fields

    def login(self, driver: webdriver.Chrome):
        driver.get(self.__url)
        if "login" in driver.page_source.lower():
            self.__login_fields.user_name.fill(self.__credentials.user_name, driver)
            self.__login_fields.password.fill(self.__credentials.password, driver)
            self.__login_fields.submit_button.click(driver)
            driver.get(self.__url)


if __name__ == '__main__':
    d = webdriver.Chrome(executable_path="../../resources/drivers/chromedriver/macos/version_87/chromedriver")
    login = Login(
        Credentials(
            user_name="admin",
            password="FMIAdm!n"
        ),
        LoginFields(
            user_name=html.HTMLTextInput(html.CSSXPath('//*[@id="username"]')),
            password=html.HTMLTextInput(html.CSSXPath('//*[@id="password"]')),
            submit_button=html.HTMLButton(html.CSSXPath('/html/body/div/div/form/p[3]/input'))
        )
    )

    d.get("http://localhost:5000/login")
    login.login(d)
    if "login" in d.page_source.lower():
        print("success")
    else:
        print("not success")

    d.close()
