from collections import namedtuple

from selenium import webdriver
import LWTest.web.interface.htmlelements as html


Credentials = namedtuple("Credentials", "user_name password")
LoginFields = namedtuple("LoginFields", "user_name password submit_button")


class Login:
    def __init__(self, credentials: Credentials, login_fields: LoginFields):
        self.__credentials = credentials
        self.__login_fields = login_fields

    def login(self, driver: webdriver.Chrome):
        self.__login_fields.user_name.fill(self.__credentials.user_name, driver)
        self.__login_fields.password.fill(self.__credentials.password, driver)
        self.__login_fields.submit_button.click(driver)


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
