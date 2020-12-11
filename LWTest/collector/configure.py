from time import sleep
from typing import List

from selenium import webdriver

import LWTest.web.interface.page as webpage
from LWTest.constants import dom, lwt

TEMPERATURE_SELECTOR = "input[type='text']"
RAW_CONFIG_SELECTOR = "input[type='number']"
PHASE_ANGLE_SELECTOR = "input[name^='correction_angle']"

_VOLTAGE_TEMPERATURE_SCALE = "-0.00012"
_REMAINING_TEMPERATURE_FIELDS_CONFIGURATION_VALUE = "0"
_SCALE_CURRENT = "0.02525"
_SCALE_VOLTAGE = "1.50000"
_SCALE_RAW_TEMP = "0.0029"
_OFFSET_RAW_TEMP = "-65.52"
_CORRECTION_ANGLE = "0.0"
_CORRECTION_VOLTAGE_SCALE = "120"
_FAULT_10K = "0.65019"
_FAULT_25K = "2.6"
_VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR = "0.0305327"
_PHASE_ANGLE = "25.8"
_NUMBER_OF_VOLTAGE_TEMPERATURE_SCALE_FIELDS = 6
_NUMBER_OF_FIELDS_TO_SKIP = 6


def _set_field(field, value):
    field.clear()
    field.send_keys(value)


def _enter_constants(fields, value):
    for field in fields:
        _set_field(field, value)


def _set_temperature_configuration_values(driver: webdriver.Chrome) -> None:
    fields = driver.find_elements_by_css_selector(TEMPERATURE_SELECTOR)
    _enter_constants(fields[0:_NUMBER_OF_VOLTAGE_TEMPERATURE_SCALE_FIELDS], _VOLTAGE_TEMPERATURE_SCALE)
    _enter_constants(fields[_NUMBER_OF_FIELDS_TO_SKIP:], _REMAINING_TEMPERATURE_FIELDS_CONFIGURATION_VALUE)


def _set_raw_configuration_values(driver: webdriver.Chrome) -> None:
    config_constants = [
        _SCALE_CURRENT,
        _SCALE_VOLTAGE,
        _SCALE_RAW_TEMP,
        _OFFSET_RAW_TEMP,
        _CORRECTION_ANGLE,
        _CORRECTION_VOLTAGE_SCALE,
        _FAULT_10K,
        _FAULT_25K,
    ]

    if "phase 4" in driver.page_source.lower():
        offsets = [0, 6, 12, 18, 24, 30, 36, 42]
        columns = 6
    else:
        offsets = [0, 3, 6, 9, 12, 15, 18, 21]
        columns = 3

    fields = driver.find_elements_by_css_selector(RAW_CONFIG_SELECTOR)
    for index in range(0, 8):
        _enter_constants(fields[offsets[index]:offsets[index] + columns], config_constants[index])


def _set_collector_calibration_factor(driver: webdriver.Chrome) -> None:
    field = driver.find_element_by_xpath(dom.vrt_calibration_factor)
    _set_field(field, _VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR)


def do_advanced_configuration(driver: webdriver.Chrome, page, submit_buttons: List[webpage.Submit]) -> None:
    temperature_submit, raw_config_submit, ride_through_submit = submit_buttons

    page.get(lwt.URL_TEMPERATURE, driver)

    operations = [
        [
            lwt.URL_TEMPERATURE,
            _set_temperature_configuration_values,
            temperature_submit
        ],
        [
            lwt.URL_RAW_CONFIGURATION,
            _set_raw_configuration_values,
            raw_config_submit
        ],
        [
            lwt.URL_VOLTAGE_RIDE_THROUGH,
            _set_collector_calibration_factor,
            ride_through_submit
        ]
    ]

    for url, func, submit_button in operations:
        driver.get(url)
        func(driver)
        submit_button.click(driver)
        sleep(lwt.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)


def configure_phase_angle(url: str, driver: webdriver.Chrome, submit_button: webpage.Submit) -> bool:
    """Enters the Phase Angle displayed on the Yokogawa into the Correction Angle field on the Configuration page."""
    driver.get(url)

    if "Sensor Configuration" not in driver.page_source:
        return False

    fields = driver.find_elements_by_css_selector(PHASE_ANGLE_SELECTOR)
    _enter_constants(fields, _PHASE_ANGLE)
    submit_button.click(driver)

    sleep(lwt.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)

    return True
