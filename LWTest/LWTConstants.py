import datetime
from enum import Enum, auto, unique, IntEnum


TESTING = True


class TestID(Enum):
    RSSI = auto()
    HIGH_VOLTAGE_TEST = auto()
    LOW_VOLTAGE_TEST = auto()
    SCALE_VALUES = auto()
    PERSISTENCE = auto()
    FAULT_CURRENT = auto()
    AMBIENT_TEMPERATURE = auto()


@unique
class TableColumn(IntEnum):
    SERIAL_NUMBER = 0
    RSSI = 1
    FIRMWARE = 2
    REPORTING = 3
    CALIBRATION = 4
    HIGH_VOLTAGE = 5
    HIGH_CURRENT = 6
    HIGH_POWER_FACTOR = 7
    HIGH_REAL_POWER = 8
    LOW_VOLTAGE = 9
    LOW_CURRENT = 10
    LOW_POWER_FACTOR = 11
    LOW_REAL_POWER = 12
    SCALE_CURRENT = 13
    SCALE_VOLTAGE = 14
    CORRECTION_ANGLE = 15
    PERSISTS = 16
    TEMPERATURE = 17
    FAULT_CURRENT = 18


class Tolerance(Enum):
    HIGH_VOLTAGE_MIN = 13786.2
    HIGH_VOLTAGE_MAX = 13813.2
    HIGH_CURRENT_MIN = 119.88
    HIGH_CURRENT_MAX = 120.12
    HIGH_POWER_MIN = 1482948.0
    HIGH_POWER_MAX = 1497852.0

    LOW_VOLTAGE_MIN = 7192.8
    LOW_VOLTAGE_MAX = 7207.2
    LOW_CURRENT_MIN = 59.94
    LOW_CURRENT_MAX = 60.06
    LOW_POWER_MIN = 386856.0
    LOW_POWER_MAX = 390744.0

    SCALE_CURRENT_MIN = 0.02375
    SCALE_CURRENT_MAX = 0.02625
    SCALE_VOLTAGE_MIN = 1.2
    SCALE_VOLTAGE_MAX = 1.8
    CORRECTION_ANGLE_MIN = -45.0
    CORRECTION_ANGLE_MAX = 45.0

    TEMPERATURE_DELTA = 15.0


LATEST_FIRMWARE_VERSION_NUMBER = "0x75"
UPGRADE_SUCCESS_TEXT = "Program Checksum is 0x3d07"
UPGRADE_FAILURE_TEXT = "Failed to enter program mode"


if TESTING:
    class TimeOut(Enum):
        COLLECTOR_POWER_OFF_TIME = 5
        URL_REQUEST = 10
        URL_READ_INTERVAL = 2
        CONFIRM_SERIAL_CONFIG = 5
        COLLECTOR_BOOT_WAIT_TIME = 3
        LINK_CHECK = 5
        LINK_PAGE_LOAD_INTERVAL = 1
        WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE = 1
        UPGRADE_LOG_LOAD_INTERVAL = 0.1
else:
    class TimeOut(Enum):
        COLLECTOR_POWER_OFF_TIME = 300  # time to wait while collector is powered off
        URL_REQUEST = 5  # timeout passed to urllib.get
        URL_READ_INTERVAL = 2  # time to wait between successive url requests
        CONFIRM_SERIAL_CONFIG = 300  # time to wait for collector to update serial number list
        COLLECTOR_BOOT_WAIT_TIME = 180  # time to wait for collector to reboot and start serving data
        LINK_CHECK = 1500  # time to wait for a sensor to link
        LINK_PAGE_LOAD_INTERVAL = 1
        WAIT_FOR_COLLECTOR_TO_START_UPDATING_LOG_FILE = 3
        UPGRADE_LOG_LOAD_INTERVAL = 1


if TESTING:
    URL_CONFIGURATION = "http://127.0.0.1:8080/LineWatch-M Website configuration.html"
    URL_MODEM_STATUS = "http://127.0.0.1:8080/LineWatch-M Website modem status.html"
    URL_UPGRADE = "http://127.0.0.1:8080/LineWatch-M%20Website%20software%20upgrade.html"
    URL_UPGRADE_LOG = r"LWTest\tests\webpages\software upgrade example 1 mod 1.html"
    # URL_UPGRADE_LOG = r"LWTest\tests\webpages\software upgrade example of failure.html"
    URL_SENSOR_DATA = "http://127.0.0.1:8080/LineWatch-M%20Website%20sensor%20data.html"
    URL_TEMPERATURE = "http://127.0.0.1:8080/LineWatch-M%20Website%20temperature%20scale.html"
    URL_RAW_CONFIGURATION = "http://127.0.0.1:8080/LineWatch-M%20Website%20raw%20configuration.html"
    URL_CALIBRATE = ""
    URL_FAULT_CURRENT = "http://127.0.0.1:8080/LineWatch-M%20Website%20fault_current.html"
    URL_VOLTAGE_RIDE_THROUGH = "http://127.0.0.1:8080/LineWatch-M%20Website%20voltage%20ride%20through%200305327.html"
else:
    URL_CONFIGURATION = "http://192.168.2.1/index.php/main/configuration"
    URL_MODEM_STATUS = "http://192.168.2.1/index.php/main/modem_status"
    URL_UPGRADE = "http://192.168.2.1/index.php/upgrade"

    date = datetime.datetime.now()
    file = f"{date.year}-{date.month:02d}-{date.day:02d}_UPDATER.txt"
    URL_UPGRADE_LOG = f"http://192.168.2.1/index.php/log_viewer/view/{file}"

    URL_SENSOR_DATA = "http://192.168.2.1/index.php/main/sensordata"
    URL_TEMPERATURE = "http://192.168.2.1/index.php/main/Temperature"
    URL_RAW_CONFIGURATION = "http://192.168.2.1/index.php/main/test"
    URL_CALIBRATE = "http://192.168.2.1/index.php/main/calibrate"
    URL_FAULT_CURRENT = "http://192.168.2.1/index.php/main/viewdata/cbc"
    URL_VOLTAGE_RIDE_THROUGH = "http://192.168.2.1/index.php/snow_ctrl/config"

VOLTAGE = 0
CURRENT = 1
FACTORS = 2
POWER = 3
SCALE_CURRENT = 4
SCALE_VOLTAGE = 5
CORRECTION_ANGLE = 6
TEMPERATURE = 7

print(f"using {URL_UPGRADE_LOG} to monitor firmware upgrade")
