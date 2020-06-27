from time import sleep

from PyQt5.QtCore import QSettings

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

import LWTest.LWTConstants as LWT
from LWTest.constants import dom as dom
from LWTest.utilities import misc


_VOLTAGE_TEMPERATURE_SCALE = "-0.00012"
_REMAINING_TEMPERATURE_FIELDS_CONFIGURATION_VALUE = "0"
_SCALE_RAW_TEMP = "0.0029"
_OFFSET_RAW_TEMP = "-65.52"
_FAULT_10K = "0.65019"
_FAULT_25K = "2.6"
_VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR = "0.0305327"
_PHASE_ANGLE = "25.8"
_NUMBER_OF_VOLTAGE_TEMPERATURE_SCALE_FIELDS = 6
_NUMBER_OF_FIELDS_TO_SKIP = 6


def do_advanced_configuration(sensor_count: int, driver: webdriver.Chrome, settings: QSettings):
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
        driver.get(LWT.URL_TEMPERATURE)

    _set_temperature_configuration_values(driver)
    driver.find_element_by_xpath(dom.temperature_password).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.temperature_submit_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)
    url = LWT.URL_RAW_CONFIGURATION
    driver.get(url)

    _set_raw_configuration_values(sensor_count, driver)
    driver.find_element_by_xpath(dom.raw_config_password).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.raw_config_submit_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)
    url = LWT.URL_VOLTAGE_RIDE_THROUGH
    driver.get(url)

    _set_collector_calibration_factor(driver)
    driver.find_element_by_xpath(dom.vrt_admin_password_field).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.vrt_save_configuration_button), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)


def configure_correction_angle(sensor_count: int, url: str, driver: webdriver.Chrome, settings: QSettings) -> bool:
    columns = LWT.THREE_SENSOR_COLUMNS if sensor_count <= 3 else LWT.SIX_SENSOR_COLUMNS
    driver.get(url)

    if "Sensor Configuration" not in driver.page_source:
        return False
    # if misc.page_failed_to_load(driver, '//*[@id="maindiv"]/form/div[1]/h1[1]'):
    #     return False

    for element in dom.correction_angle_elements[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_PHASE_ANGLE)

    driver.find_element_by_xpath(dom.configuration_password).send_keys(settings.value("main/config_password"))
    _submit(driver.find_element_by_xpath(dom.configuration_save_changes), settings)

    sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)

    return True


def _set_temperature_configuration_values(driver: webdriver.Chrome) -> None:
    for element in dom.temperature_scale_offset[0:_NUMBER_OF_VOLTAGE_TEMPERATURE_SCALE_FIELDS]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_VOLTAGE_TEMPERATURE_SCALE)

    for element in dom.temperature_scale_offset[_NUMBER_OF_FIELDS_TO_SKIP:]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_REMAINING_TEMPERATURE_FIELDS_CONFIGURATION_VALUE)


def _set_raw_configuration_values(sensor_count: int, driver: webdriver.Chrome) -> None:
    columns = 3 if sensor_count <= 3 else 6

    for element in dom.scale_raw_temp_elements[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_SCALE_RAW_TEMP)

    for element in dom.offset_raw_temp_elements[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_OFFSET_RAW_TEMP)

    for element in dom.fault10k[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_FAULT_10K)

    for element in dom.fault25k[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_FAULT_25K)


def _set_collector_calibration_factor(driver: webdriver.Chrome) -> None:
    cal_factor = driver.find_element_by_xpath(dom.vrt_calibration_factor)
    cal_factor.clear()
    cal_factor.send_keys(_VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR)


def _submit(element, settings: QSettings) -> None:
    if settings.value("DEBUG") == 'true':
        return

    element.click()
