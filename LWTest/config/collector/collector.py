# collector.py
import logging
from collections import namedtuple
from typing import List, Callable, Any

from PyQt5.QtCore import QSettings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from laboot.config.dom.search import SearchDom
from laboot.utilities.utilities import to_bool

ConfigurationResult = namedtuple("ConfigurationResult", "result exc message")


class CollectorConfigurator:
    def __init__(self):
        settings = QSettings()

        self.driver_executable = settings.value("drivers/chromedriver")
        self.configuration_url = settings.value("pages/configuration")
        self.config_password = settings.value("main/config_password")
        self.service_log_path = r"laboot\resources\logs\chromewebdriver._log"
        self.correction_angle = "25.8"

        if to_bool(settings.value("ui/menus/options/headless")):
            options = Options()
            options.headless = True
            self.browser = self._get_web_driver(options=options)
        else:
            self.browser = self._get_web_driver()

    def configure_serial_numbers(self, serial_numbers: tuple) -> ConfigurationResult:
        # BUG: app will probably shit the bed if the user login page is displayed
        logger = logging.getLogger(__name__)
        logger.info("Configuring serial numbers.")
        logger.debug(f"Using serial numbers: {serial_numbers}")

        return self._configure_collector(serial_numbers, self.configuration_url, self._configure_serial_numbers)

    def configure_correction_angle(self) -> ConfigurationResult:
        logger = logging.getLogger(__name__)
        logger.info("Configuring correction angle.")

        return self._configure_collector(self.correction_angle,
                                         self.configuration_url,
                                         self._configure_correction_angles)

    def close_browser(self):
        self.browser.quit()

    def _configure_collector(self, data: Any, url: str, func: Callable) -> ConfigurationResult:
        # TODO: see if better type hint than Any for data
        # TODO: figure out some sort of exception handling
        """Configures the collector with values for test.

        Parameters
        ----------
        data: (str, list)
            the values to enter into the collector

        url: str
            the url where the data will be entered

        func: Callable
            this function will be called with 'data' and is responsible
            for performing the task of configuring the collector i.e., func(data)

        Returns
        -------
            True if the collector was successfully configured.
            False if an error occurred."""
        logger = logging.getLogger(__name__)

        self.browser.get(url)

        if "offline" in self.browser.page_source:
            print("There appears to be a network issue. The browser reports 'No internet'.")
            return ConfigurationResult(False, None, "Unable to load website.")

        # TODO: some how, some day verify this will work
        if "trigger text" in self.browser.current_url:
            self._handle_admin_login()
            self.browser.get(url)

        func(data)

        self._select_60_hz()
        self._disable_voltage_ride_through()

        self._submit_changes()

        return ConfigurationResult(result=True, exc=None, message=None)

    def _configure_serial_numbers(self, serial_numbers: List[str]):
        """Must receive a list of 6 strings representing numeric values."""
        logger = logging.getLogger(__name__)
        serial_inputs = SearchDom.for_serial_input_elements(self.browser)

        # TODO: could slice serial_inputs to use only the number of elements equal to the length of serial_numbers arg
        for index, serial_input in enumerate(serial_inputs[:len(serial_numbers)]):
            serial_input.clear()
            serial_input.send_keys(serial_numbers[index])

        logger.debug(f"Collector configured with serial numbers: {serial_numbers}")

    def _configure_correction_angles(self, correction_angle: str):
        logger = logging.getLogger(__name__)
        angle_inputs = SearchDom.for_angle_input_elements(self.browser)

        for index, angle_input in enumerate(angle_inputs):
            print(f"configuring {angle_input} with {correction_angle}")
            angle_input.clear()
            angle_input.send_keys(correction_angle)

        logger.debug(f"Collector correction angle configured with '{correction_angle}'")

    def _disable_voltage_ride_through(self):
        logger = logging.getLogger(__name__)
        logger.info("Disabling Voltage Ride Through.")

        vrt = SearchDom.for_voltage_ride_through_radio_button_element(self.browser)
        logger.debug(f"Voltage Ride Through checked state: {vrt.is_selected()}")
        if vrt.is_selected():
            vrt.click()

    def _select_60_hz(self):
        logger = logging.getLogger(__name__)
        logger.info("Selecting 60Hz")

        SearchDom.for_sixty_hz_radio_button_element(self.browser).click()

    def _get_web_driver(self, options=None):
        # TODO: add exception handling

        return webdriver.Chrome(executable_path=self.driver_executable,
                                service_log_path=self.service_log_path,
                                options=options)

    def _handle_admin_login(self):
        pass

    def _submit_changes(self):
        logger = logging.getLogger(__name__)
        logger.info("Saving changes to the collector.")

        SearchDom.for_password_input_element(self.browser).send_keys(self.config_password)
        SearchDom.for_save_config_button(self.browser).click()

        logger.info("Changes saved.")


# TODO: Will have to account for the times when the administration pages rears it's head
# TODO: Need to implement exception handling
#       - program crashes with a url that can't be reached, found, etc. in configure()
#           - Fixed: now check browser.page_source for presence of "offline", if present return
