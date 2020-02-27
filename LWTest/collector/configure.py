from time import sleep

from PyQt5.QtCore import QSettings

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

import LWTest.LWTConstants as LWT
from LWTest.constants import dom as dom
from LWTest.utilities import misc


def do_advanced_configuration(count: int, browser: webdriver.Chrome):
    settings = QSettings()
    url = LWT.URL_TEMPERATURE
    browser.get(url)

    try:
        # If we end up on the login page.
        browser.find_element_by_xpath(dom.login_header)
        browser.find_element_by_xpath(dom.login_username_field).send_keys(settings.value("main/admin_user"))
        browser.find_element_by_xpath(dom.login_password_field).send_keys(settings.value("main/admin_password"))
        browser.find_element_by_xpath(dom.login_button).click()
    except NoSuchElementException:
        pass
    finally:
        sleep(2)
        browser.get(LWT.URL_TEMPERATURE)

    for element in dom.temperature_scale_offset[0:6]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("-0.00012")

    for element in dom.temperature_scale_offset[6:]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("0")

    browser.find_element_by_xpath(dom.temperature_password).send_keys(settings.value("main/config_password"))
    _submit(browser.find_element_by_xpath(dom.temperature_submit_button), url)

    sleep(2)
    url = LWT.URL_RAW_CONFIGURATION
    browser.get(url)

    for element in dom.scale_raw_temp_elements[0:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("0.0029")

    for element in dom.offset_raw_temp_elements[0:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("-65.52")

    for element in dom.fault10k[0:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("0.65019")

    for element in dom.fault25k[0:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("2.6")

    browser.find_element_by_xpath(dom.raw_config_password).send_keys(settings.value("main/config_password"))
    _submit(browser.find_element_by_xpath(dom.raw_config_submit_button), url)

    sleep(2)
    url = LWT.URL_VOLTAGE_RIDE_THROUGH
    browser.get(url)

    cal_factor = browser.find_element_by_xpath(dom.vrt_calibration_factor)
    cal_factor.clear()
    cal_factor.send_keys("0.0305327")

    browser.find_element_by_xpath(dom.vrt_admin_password_field).send_keys(settings.value("main/config_password"))
    _submit(browser.find_element_by_xpath(dom.vrt_save_configuration_button), url)

    sleep(2)


def configure_correction_angle(url: str, browser: webdriver.Chrome, count: int):
    settings = QSettings()
    browser.get(url)

    if misc.page_failed_to_load(browser, '//*[@id="maindiv"]/form/div[1]/h1[1]'):
        return True

    for element in dom.correction_angle_elements[:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys("25.8")

    browser.find_element_by_xpath(dom.configuration_password).send_keys(settings.value("main/config_password"))
    _submit(browser.find_element_by_xpath(dom.configuration_save_changes), url)

    sleep(1)


def _submit(element, url):
    if '127.0.0.1' in url:
        return

    element.click()
