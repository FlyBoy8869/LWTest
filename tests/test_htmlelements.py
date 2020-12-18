import http.server

from unittest import TestCase

from selenium import webdriver

import LWTest.web.interface.htmlelements as html


class TestCSSXPath(TestCase):
    def setUp(self) -> None:
        self.selector_text = '//*[@id="username"]'

    def test_selector(self):
        css_selector = html.CSSXPath(self.selector_text)
        self.assertEqual(self.selector_text, css_selector.selector)

    def test_selector_exception(self):
        self.assertRaises(AssertionError, html.CSSXPath, 42)


class TestHTMLFillable(TestCase):
    def setUp(self) -> None:
        self.driver = webdriver.Chrome(
            executable_path="../LWTest/resources/drivers/chromedriver/macos/version_87/chromedriver"
        )
        self.selector_text = "/html/head/title"

    # def test_get_content(self):
    #     element = html.HTMLFillable(html.CSSXPath(self.selector_text))
    #     self.driver.get("localhost:6969/htmlelements.html")
    #     self.assertEqual("HTMLElements Test Page", element.get_text_content(self.driver))
