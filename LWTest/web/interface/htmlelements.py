from selenium import webdriver


class CSSXPath:
    def __init__(self, xpath: str):
        self.__path = xpath

    @property
    def selector(self):
        return self.__path


class HTMLElement:
    def __init__(self, selector: CSSXPath):
        assert isinstance(selector, CSSXPath), "selector must type CSSXPath"
        self._selector: CSSXPath = selector

    def get_element(self, driver: webdriver.Chrome):
        return driver.find_element_by_xpath(self._selector.selector)


class HTMLFillable(HTMLElement):
    def fill(self, text: str, driver: webdriver.Chrome):
        element = self.get_element(driver)
        element.clear()
        element.send_keys(text)

    def get_text_content(self, driver):
        content = self.get_element(driver).get_attribute("textContent")
        return content


class HTMLClickable(HTMLElement):
    def click(self, driver: webdriver.Chrome):
        self.get_element(driver).click()


class HTMLTextInput(HTMLFillable):
    pass


class HTMLButton(HTMLClickable):
    pass
