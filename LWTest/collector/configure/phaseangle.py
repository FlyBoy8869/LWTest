from selenium import webdriver

from LWTest.collector.common import helpers
from LWTest.collector.configure.raw import _logger, PHASE_ANGLE_SELECTOR, _PHASE_ANGLE
from LWTest.web.interface import page as webpage


def configure_phase_angle(url: str, driver: webdriver.Chrome, page_loader, submit_button: webpage.Submit) -> bool:
    """Enters the Phase Angle displayed on the Yokogawa
    into the Correction Angle fields on the Configuration page."""
    _logger.debug("setting phase angle correction factor")
    page_loader.get(url, driver)
    fields = driver.find_elements_by_css_selector(PHASE_ANGLE_SELECTOR)
    helpers.enter_constants(fields, _PHASE_ANGLE)
    submit_button.click(driver)

    return True
