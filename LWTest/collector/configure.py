from time import sleep

from PyQt5.QtCore import QSettings
from selenium import webdriver

import LWTest.constants.lwt_constants as LWT
from LWTest.constants import dom as dom

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

_CONFIG_PASSWORD_KEY = "main/config_password"


def do_advanced_configuration(sensor_count: int, driver: webdriver.Chrome, settings: QSettings):
    config_password = settings.value(_CONFIG_PASSWORD_KEY)

    _login_if_necessary(driver, settings.value("main/admin_user"), settings.value("main/admin_password"))

    # url, function, function args, dom elements
    operations = [
        [
            LWT.URL_TEMPERATURE,
            _set_temperature_configuration_values,
            [],
            [dom.temperature_password, dom.temperature_submit_button]
        ],
        [
            LWT.URL_RAW_CONFIGURATION,
            _set_raw_configuration_values,
            [sensor_count],
            [dom.raw_config_password, dom.raw_config_submit_button]
        ],
        [
            LWT.URL_VOLTAGE_RIDE_THROUGH,
            _set_collector_calibration_factor,
            [],
            [dom.vrt_admin_password_field, dom.vrt_save_configuration_button]
        ]
    ]

    for url, func, args, dom_elements in operations:
        driver.get(url)
        func(driver, *args)
        _enter_password_and_submit(driver, config_password, *dom_elements)
        sleep(LWT.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)


def configure_correction_angle(sensor_count: int, url: str, driver: webdriver.Chrome, settings: QSettings) -> bool:
    columns = LWT.THREE_SENSOR_COLUMNS if sensor_count <= 3 else LWT.SIX_SENSOR_COLUMNS
    driver.get(url)

    if "Sensor Configuration" not in driver.page_source:
        return False

    for element in dom.correction_angle_elements[:columns]:
        field = driver.find_element_by_xpath(element)
        field.clear()
        field.send_keys(_PHASE_ANGLE)

    _enter_password_and_submit(driver, settings.value(_CONFIG_PASSWORD_KEY), dom.configuration_password,
                               dom.configuration_save_changes)

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


def _set_raw_configuration_values(driver: webdriver.Chrome, sensor_count: int) -> None:
    columns = LWT.THREE_SENSOR_COLUMNS if sensor_count <= 3 else LWT.SIX_SENSOR_COLUMNS

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


def _submit(driver, element) -> None:
    driver.find_element_by_xpath(element).click()


def _enter_password_and_submit(driver, config_password, password_element, submit_button):
    driver.find_element_by_xpath(password_element).send_keys(config_password)
    _submit(driver, submit_button)


def _login_if_necessary(driver: webdriver.Chrome, user_name: str, password: str):
    driver.get(LWT.URL_TEMPERATURE)
    if "Login" in driver.page_source:
        # Landed on the 'Login' page.
        driver.find_element_by_xpath(dom.login_username_field).send_keys(user_name)
        driver.find_element_by_xpath(dom.login_password_field).send_keys(password)
        driver.find_element_by_xpath(dom.login_button).click()
        sleep(1.0)
