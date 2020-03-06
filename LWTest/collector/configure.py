from time import sleep

from PyQt5.QtCore import QSettings

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

import LWTest.LWTConstants as LWT
from LWTest.constants import dom as dom
from LWTest.utilities import misc


_VOLTAGE_TEMPERATURE_SCALE = "-0.00012"
_REMAINING_TEMPERATURE_INPUT_FIELDS = "0"
_SCALE_RAW_TEMP = "0.0029"
_OFFSET_RAW_TEMP = "-65.52"
_FAULT_10K = "0.65019"
_FAULT_25K = "2.6"
_VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR = "0.0305327"
_PHASE_ANGLE = "25.8"


def do_advanced_configuration(count: int, driver: webdriver.Chrome, settings: QSettings):
    url = LWT.URL_TEMPERATURE
    driver.get(url)

    try:
        # If we end up on the login page.
        driver.find_element_by_xpath(dom.login_header)
        driver.find_element_by_xpath(dom.login_username_field).send_keys(settings.value("main/admin_user"))
        driver.find_element_by_xpath(dom.login_password_field).send_keys(settings.value("main/admin_password"))
        driver.find_element_by_xpath(dom.login_button).click()
    except NoSuchElementException:
        pass
    finally:
        # sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)
        driver.get(LWT.URL_TEMPERATURE)

    _set_temperature_configuration_values(driver)
    driver.find_element_by_xpath(dom.temperature_password).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.temperature_submit_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)
    url = LWT.URL_RAW_CONFIGURATION
    driver.get(url)

    _set_raw_configuration_values(count, driver)
    driver.find_element_by_xpath(dom.raw_config_password).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.raw_config_submit_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)
    url = LWT.URL_VOLTAGE_RIDE_THROUGH
    driver.get(url)

    _set_collector_calibration_factor(driver)
    driver.find_element_by_xpath(dom.vrt_admin_password_field).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.vrt_save_configuration_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)


def configure_correction_angle(url: str, browser: webdriver.Chrome, count: int) -> bool:
    settings = QSettings()
    browser.get(url)

    if misc.page_failed_to_load(browser, '//*[@id="maindiv"]/form/div[1]/h1[1]'):
        return True

    for element in dom.correction_angle_elements[:count]:
        field = browser.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_PHASE_ANGLE)

    browser.find_element_by_xpath(dom.configuration_password).send_keys(settings.value("main/config_password"))
    _submit(browser.find_element_by_xpath(dom.configuration_save_changes), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)

    return False


def _set_temperature_configuration_values(driver: webdriver.Chrome) -> None:
    for element in dom.temperature_scale_offset[0:6]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_VOLTAGE_TEMPERATURE_SCALE)

    for element in dom.temperature_scale_offset[6:]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_REMAINING_TEMPERATURE_INPUT_FIELDS)


def _set_raw_configuration_values(number_of_sensors: int, driver: webdriver.Chrome) -> None:
    for element in dom.scale_raw_temp_elements[0:number_of_sensors]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_SCALE_RAW_TEMP)

    for element in dom.offset_raw_temp_elements[0:number_of_sensors]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_OFFSET_RAW_TEMP)

    for element in dom.fault10k[0:number_of_sensors]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_FAULT_10K)

    for element in dom.fault25k[0:number_of_sensors]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_FAULT_25K)


def _set_collector_calibration_factor(driver: webdriver.Chrome) -> None:
    cal_factor = driver.find_element_by_xpath(dom.vrt_calibration_factor)
    cal_factor.clear()
    cal_factor.send_keys(_VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR)


def _submit(element, settings: QSettings):
    if settings.value("DEBUG") == 'true':
        return

    element.click()
