from enum import Enum


class TimeOut(Enum):
    COLLECTOR_POWER_OFF_TIME = 300  # time to wait while collector is powered off
    URL_REQUEST = 5  # _timeout passed to urllib.get
    URL_READ_INTERVAL = 2  # time to wait between successive _url requests
    CONFIRM_SERIAL_CONFIG = 300  # time to wait for collector to update serial number list
    COLLECTOR_BOOT_WAIT_TIME = 180  # time to wait for collector to reboot and start serving data
    LINK_CHECK = 120  # time to wait for a sensor to link
    LINK_PAGE_LOAD_INTERVAL = 1
    WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE = 3
    UPGRADE_LOG_LOAD_INTERVAL = 1
    TIME_BETWEEN_CONFIGURATION_PAGES = 3
