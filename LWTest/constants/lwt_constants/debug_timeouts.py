from enum import Enum


class TimeOut(Enum):
    COLLECTOR_POWER_OFF_TIME = 2
    URL_REQUEST = 5
    URL_READ_INTERVAL = 2
    CONFIRM_SERIAL_CONFIG = 20
    COLLECTOR_BOOT_WAIT_TIME = 25
    LINK_CHECK = 13
    LINK_PAGE_LOAD_INTERVAL = 1  # time to sleep between successive loads of the modem status page
    WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE = 1
    UPGRADE_LOG_LOAD_INTERVAL = 0.1
    TIME_BETWEEN_CONFIGURATION_PAGES = 0
