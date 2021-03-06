# spreadsheet.dom.py

from collections import namedtuple


# usage:
# from LWTest.spreadsheet import constants as sc
# phase = sc.PhaseReadingsCells(*sc.phase_1_cells)
#
# Note: do not change the order of arguments
# or else readings will end up in the wrong place
PhaseReadingsCells = namedtuple("PhaseReadingsCells", "high_voltage high_current high_power_factor " +
                                "high_real_power low_voltage low_current low_power_factor low_real_power " +
                                "scale_current scale_voltage correction_angle persists " +
                                "firmware_version reporting_data rssi calibrated temperature fault_current")

high_reference_cells = ('D22', 'D23', 'D24', 'D25')

low_reference_cells = ('D27', 'D28', 'D29', 'D30')

phase_1_cells = ('E22', 'E23', 'E24', 'E25',
                 'E27', 'E28', 'E29', 'E30',
                 'D34', 'D35', 'D36', 'D38',
                 'D6', 'D7', 'D8', 'D16',
                 'D17', 'D18')

phase_2_cells = ('F22', 'F23', 'F24', 'F25',
                 'F27', 'F28', 'F29', 'F30',
                 'E34', 'E35', 'E36', 'E38',
                 'E6', 'E7', 'E8', 'E16',
                 'E17', 'E18')

phase_3_cells = ('G22', 'G23', 'G24', 'G25',
                 'G27', 'G28', 'G29', 'G30',
                 'F34', 'F35', 'F36', 'F38',
                 'F6', 'F7', 'F8', 'F16',
                 'F17', 'F18')

phase_4_cells = ('H22', 'H23', 'H24', 'H25',
                 'H27', 'H28', 'H29', 'H30',
                 'G34', 'G35', 'G36', 'G38',
                 'G6', 'G7', 'G8', 'G16',
                 'G17', 'G18')

phase_5_cells = ('I22', 'I23', 'I24', 'I25',
                 'I27', 'I28', 'I29', 'I30',
                 'H34', 'H35', 'H36', 'H38',
                 'H6', 'H7', 'H8', 'H16',
                 'H17', 'H18')

phase_6_cells = ('J22', 'J23', 'J24', 'J25',
                 'J27', 'J28', 'J29', 'J30',
                 'I34', 'I35', 'I36', 'I38',
                 'I6', 'I7', 'I8', 'I16',
                 'I17', 'I18')

phases_cells = (phase_1_cells, phase_2_cells, phase_3_cells, phase_4_cells, phase_5_cells, phase_6_cells)

temperature_reference = 'C17'

WATCHDOG_LOG = 'C43'
SENSOR_COMM_LOG = 'C44'
UPDATER_LOG = 'C45'

LOG_FILE_CELLS = [WATCHDOG_LOG, SENSOR_COMM_LOG, UPDATER_LOG]

# locations order Sensor1 Sensor2 Sensor3 Sensor4 Sensor5 Sensor6
SERIAL_LOCATIONS = ["D4", "E4", "F4", "G4", "H4", "I4"]
FIVE_AMP_SAVE_LOCATIONS = ["D5", "E5", "F5", "G5", "H5", "I5"]

tested_by = 'E43'
test_date = 'I43'

WORKSHEET_NAME = "Sensor(s)"
