import datetime

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
URL_FAULT_CURRENT = "http://192.168.2.1/index.php/main/viewdata/fault_current"
URL_VOLTAGE_RIDE_THROUGH = "http://192.168.2.1/index.php/snow_ctrl/config"
URL_LOG_FILES = 'http://192.168.2.1/downloadLogs.php'
