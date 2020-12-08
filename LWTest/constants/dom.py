# config.dom.dom.py
from PyQt5.QtCore import QSettings


TESTING = True if QSettings().value("DEBUG") == 'true' else False

login_header = '/html/body/div/h1'
LOGIN_USERNAME_FIELD = '//*[@id="username"]'
LOGIN_PASSWORD_FIELD = '//*[@id="password"]'
LOGIN_BUTTON = '/html/body/div/div/form/p[3]/input'

# Configuration elements
serial_number_elements = ('//*[@id="maindiv"]/form/div[1]/div[2]/div[3]/input',
                          '//*[@id="maindiv"]/form/div[1]/div[2]/div[4]/input',
                          '//*[@id="maindiv"]/form/div[1]/div[2]/div[5]/input',
                          '//*[@id="maindiv"]/form/div[1]/div[2]/div[6]/input',
                          '//*[@id="maindiv"]/form/div[1]/div[2]/div[7]/input',
                          '//*[@id="maindiv"]/form/div[1]/div[2]/div[8]/input')

correction_angle_elements = ('//*[@id="maindiv"]/form/div[1]/div[4]/div[3]/input',
                             '//*[@id="maindiv"]/form/div[1]/div[4]/div[4]/input',
                             '//*[@id="maindiv"]/form/div[1]/div[4]/div[5]/input',
                             '//*[@id="maindiv"]/form/div[1]/div[4]/div[6]/input',
                             '//*[@id="maindiv"]/form/div[1]/div[4]/div[7]/input',
                             '//*[@id="maindiv"]/form/div[1]/div[4]/div[8]/input')

configuration_frequency = '//*[@id="maindiv"]/form/div[3]/div[2]/div[3]/input'

voltage_ride_through = '//*[@id="singlephase"]'  # use .is_selected() to determine if it needs to be clicked

configuration_password = '//*[@id="password"]/div/input'

if TESTING:
    configuration_save_changes = '//*[@id="password"]/div/input[2]'
else:
    configuration_save_changes = '//*[@id="saveconfig"]'

#
# raw configuration data
scale_raw_temp_elements = ('//*[@id="maindiv"]/form/div[4]/div[3]/input',
                           '//*[@id="maindiv"]/form/div[4]/div[4]/input',
                           '//*[@id="maindiv"]/form/div[4]/div[5]/input',
                           '//*[@id="maindiv"]/form/div[4]/div[6]/input',
                           '//*[@id="maindiv"]/form/div[4]/div[7]/input',
                           '//*[@id="maindiv"]/form/div[4]/div[8]/input')

offset_raw_temp_elements = ('//*[@id="maindiv"]/form/div[5]/div[3]/input',
                            '//*[@id="maindiv"]/form/div[5]/div[4]/input',
                            '//*[@id="maindiv"]/form/div[5]/div[5]/input',
                            '//*[@id="maindiv"]/form/div[5]/div[6]/input',
                            '//*[@id="maindiv"]/form/div[5]/div[7]/input',
                            '//*[@id="maindiv"]/form/div[5]/div[8]/input')

fault10k = ('//*[@id="maindiv"]/form/div[8]/div[3]/input',
            '//*[@id="maindiv"]/form/div[8]/div[4]/input',
            '//*[@id="maindiv"]/form/div[8]/div[5]/input',
            '//*[@id="maindiv"]/form/div[8]/div[6]/input',
            '//*[@id="maindiv"]/form/div[8]/div[7]/input',
            '//*[@id="maindiv"]/form/div[8]/div[8]/input')

fault25k = ('//*[@id="maindiv"]/form/div[9]/div[3]/input',
            '//*[@id="maindiv"]/form/div[9]/div[4]/input',
            '//*[@id="maindiv"]/form/div[9]/div[5]/input',
            '//*[@id="maindiv"]/form/div[9]/div[6]/input',
            '//*[@id="maindiv"]/form/div[9]/div[7]/input',
            '//*[@id="maindiv"]/form/div[9]/div[8]/input')

raw_config_password = '//*[@id="password"]/div/input[1]'
raw_config_submit_button = '//*[@id="password"]/div/input[2]'

#
# Software Upgrade data
unit_select_button = ('//*[@id="maindiv"]/form/div[2]/div[3]/input',
                      '//*[@id="maindiv"]/form/div[3]/div[3]/input',
                      '//*[@id="maindiv"]/form/div[4]/div[3]/input',
                      '//*[@id="maindiv"]/form/div[5]/div[3]/input',
                      '//*[@id="maindiv"]/form/div[6]/div[3]/input',
                      '//*[@id="maindiv"]/form/div[7]/div[3]/input')

firmware_file = '//*[@id="maindiv"]/form/p[1]/input'
upgrade_password = '//*[@id="maindiv"]/form/p[2]/input'
upgrade_button = '//*[@id="maindiv"]/form/input'

#
# Temperature Voltage & Current Scale/Offset
temperature_scale_offset = ('//*[@id="maindiv"]/form/input[1]',
                            '//*[@id="maindiv"]/form/input[2]',
                            '//*[@id="maindiv"]/form/input[3]',
                            '//*[@id="maindiv"]/form/input[4]',
                            '//*[@id="maindiv"]/form/input[5]',
                            '//*[@id="maindiv"]/form/input[6]',
                            '//*[@id="maindiv"]/form/input[7]',
                            '//*[@id="maindiv"]/form/input[8]',
                            '//*[@id="maindiv"]/form/input[9]',
                            '//*[@id="maindiv"]/form/input[10]',
                            '//*[@id="maindiv"]/form/input[11]',
                            '//*[@id="maindiv"]/form/input[12]',
                            '//*[@id="maindiv"]/form/input[13]',
                            '//*[@id="maindiv"]/form/input[14]',
                            '//*[@id="maindiv"]/form/input[15]',
                            '//*[@id="maindiv"]/form/input[16]',
                            '//*[@id="maindiv"]/form/input[17]',
                            '//*[@id="maindiv"]/form/input[18]',
                            '//*[@id="maindiv"]/form/input[19]',
                            '//*[@id="maindiv"]/form/input[20]',
                            '//*[@id="maindiv"]/form/input[21]',
                            '//*[@id="maindiv"]/form/input[22]',
                            '//*[@id="maindiv"]/form/input[23]',
                            '//*[@id="maindiv"]/form/input[24]')

temperature_password = '//*[@id="maindiv"]/form/input[25]'
temperature_submit_button = '//*[@id="maindiv"]/form/input[27]'

# Voltage Ride Through - Configuration Settings
vrt_calibration_factor = '//*[@id="maindiv"]/form/div/div[6]/div[2]/input'
vrt_admin_password_field = '//*[@id="maindiv"]/form/h4[2]/input[1]'
vrt_save_configuration_button = '//*[@id="maindiv"]/form/h4[2]/input[2]'

phase_current = ('//*[@id="data"]/div[4]/div[3]',
                 '//*[@id="data"]/div[4]/div[4]',
                 '//*[@id="data"]/div[4]/div[5]',
                 '//*[@id="data"]/div[4]/div[6]',
                 '//*[@id="data"]/div[4]/div[7]',
                 '//*[@id="data"]/div[4]/div[8]')

phase_power_factor = ('//*[@id="data"]/div[5]/div[3]',
                      '//*[@id="data"]/div[5]/div[4]',
                      '//*[@id="data"]/div[5]/div[5]',
                      '//*[@id="data"]/div[5]/div[6]',
                      '//*[@id="data"]/div[5]/div[7]',
                      '//*[@id="data"]/div[5]/div[8]')

phase_lead_lag = ('//*[@id="data"]/div[6]/div[3]',
                  '//*[@id="data"]/div[6]/div[4]',
                  '//*[@id="data"]/div[6]/div[5]',
                  '//*[@id="data"]/div[6]/div[6]',
                  '//*[@id="data"]/div[6]/div[7]',
                  '//*[@id="data"]/div[6]/div[8]')

phase_real_power = ('//*[@id="data"]/div[7]/div[3]',
                    '//*[@id="data"]/div[7]/div[4]',
                    '//*[@id="data"]/div[7]/div[5]',
                    '//*[@id="data"]/div[7]/div[6]',
                    '//*[@id="data"]/div[7]/div[7]',
                    '//*[@id="data"]/div[7]/div[8]')

phase_temperature = ('//*[@id="data"]/div[17]/div[3]',
                     '//*[@id="data"]/div[17]/div[4]',
                     '//*[@id="data"]/div[17]/div[5]',
                     '//*[@id="data"]/div[17]/div[6]',
                     '//*[@id="data"]/div[17]/div[7]',
                     '//*[@id="data"]/div[17]/div[8]')

# Fault Current
fault_current_1 = '//*[@id="placeholder"]/div/div[2]/div[1]'
fault_current_2 = '//*[@id="overview"]/div/div[2]/div[1]'
