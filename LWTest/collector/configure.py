import logging
from time import sleep
from typing import List

from selenium import webdriver

import LWTest.web.interface.page as webpage
from LWTest.constants import dom, lwt

_logger = logging.getLogger(__name__)

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


def do_advanced_configuration(driver: webdriver.Chrome, page_loader, submit_buttons: List[webpage.Submit]) -> None:
    temperature_button, raw_config_button, ride_through_button = submit_buttons

    page_loader.get(lwt.URL_TEMPERATURE, driver)

    # url, function, submit button
    operations = [
        [
            lwt.URL_TEMPERATURE,
            _set_temperature_configuration_values,
            temperature_button
        ],
        [
            lwt.URL_RAW_CONFIGURATION,
            _set_raw_configuration_values,
            raw_config_button
        ],
        [
            lwt.URL_VOLTAGE_RIDE_THROUGH,
            _set_collector_calibration_factor,
            ride_through_button
        ]
    ]

    for url, config_func, submit_button in operations:
        page_loader.get(url, driver)
        config_func(driver)
        submit_button.click(driver)
        sleep(lwt.TimeOut.TIME_BETWEEN_CONFIGURATION_PAGES.value)


def configure_phase_angle(url: str, driver: webdriver.Chrome, page_loader, submit_button: webpage.Submit) -> bool:
    """Enters the Phase Angle displayed on the Yokogawa into the Correction Angle fields on the Configuration page."""
    _logger.debug("setting phase angle correction factor")
    page_loader.get(url, driver)
    fields = driver.find_elements_by_css_selector(PHASE_ANGLE_SELECTOR)
    _enter_constants(fields, _PHASE_ANGLE)
    submit_button.click(driver)

    return True


# -- private module functions ---
def _set_field(field, value):
    field.clear()
    field.send_keys(value)


def _enter_constants(fields, value):
    for field in fields:
        _set_field(field, value)


def _set_temperature_configuration_values(driver: webdriver.Chrome) -> None:
    _logger.debug("setting temperature constants")
    fields = driver.find_elements_by_css_selector(TEMPERATURE_SELECTOR)
    _enter_constants(fields[0:_NUMBER_OF_VOLTAGE_TEMPERATURE_SCALE_FIELDS], _VOLTAGE_TEMPERATURE_SCALE)
    _enter_constants(fields[_NUMBER_OF_FIELDS_TO_SKIP:], _REMAINING_TEMPERATURE_FIELDS_CONFIGURATION_VALUE)


def _set_raw_configuration_values(driver: webdriver.Chrome) -> None:
    _logger.debug("setting raw configuration constants")
    values_to_configure = (
        (_SCALE_CURRENT, "input[type='number'][name^='scaleCurrent'"),
        (_SCALE_VOLTAGE, "input[type='number'][name^='scaleVoltage'"),
        (_SCALE_RAW_TEMP, "input[type='number'][name^='scaleRaw'"),
        (_OFFSET_RAW_TEMP, "input[type='number'][name^='offsetRaw'"),
        (_CORRECTION_ANGLE, "input[type='number'][name^='correctionAngle'"),
        (_CORRECTION_VOLTAGE_SCALE, "input[type='number'][name^='correctionVoltageScale'"),
        (_FAULT_10K, "input[type='number'][name^='fault10k'"),
        (_FAULT_25K, "input[type='number'][name^='fault25k'")
    )

    for config_constant, selector in values_to_configure:
        _enter_constants(driver.find_elements_by_css_selector(selector), config_constant)


def _set_collector_calibration_factor(driver: webdriver.Chrome) -> None:
    _logger.debug("setting calibration factor constant")
    field = driver.find_element_by_xpath(dom.vrt_calibration_factor)
    _set_field(field, _VOLTAGE_RIDE_THROUGH_CALIBRATION_FACTOR)
