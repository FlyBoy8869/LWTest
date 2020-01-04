# spreadsheet.constants.py

from collections import namedtuple


# usage:
# from LWTest.spreadsheet import constants as sc
# phase = sc.PhaseReadings(*sc.phase_1)
#
# Note: do not change the order of arguments
# or else readings will end up in the wrong place
PhaseReadings = namedtuple('PhaseReadings', "high_voltage high_current high_power_factor high_real_power " +
                           "low_voltage low_current low_power_factor low_real_power " +
                           "scale_current scale_voltage correction_angle persists " +
                           "firmware_version reporting_data rssi temperature fault_current")

high_reference = ('D22', 'D23', 'D24', 'D25')

low_reference = ('D27', 'D28', 'D29', 'D30')

phase_1 = ('E22', 'E23', 'E24', 'E25',
           'E27', 'E28', 'E29', 'E30',
           'D34', 'D35', 'D36', 'D38',
           'D6', 'D7', 'D8', 'D17', 'D18')

phase_2 = ('F22', 'F23', 'F24', 'F25',
           'F27', 'F28', 'F29', 'F30',
           'E34', 'E35', 'E36', 'E38',
           'E6', 'E7', 'E8', 'E17', 'E18')

phase_3 = ('G22', 'G23', 'G24', 'G25',
           'G27', 'G28', 'G29', 'G30',
           'F34', 'F35', 'F36', 'F38',
           'F6', 'F7', 'F8', 'F17', 'F18')

phase_4 = ('H22', 'H23', 'H24', 'H25',
           'H27', 'H28', 'H29', 'H30',
           'G34', 'G35', 'G36', 'G38',
           'G6', 'G7', 'G8', 'G17', 'G18')

phase_5 = ('I22', 'I23', 'I24', 'I25',
           'I27', 'I28', 'I29', 'I30',
           'H34', 'H35', 'H36', 'H38',
           'H6', 'H7', 'H8', 'H17', 'H18')

phase_6 = ('J22', 'J23', 'J24', 'J25',
           'J27', 'J28', 'J29', 'J30',
           'I34', 'I35', 'I36', 'I38',
           'I6', 'I7', 'I8', 'I17', 'I18')

phases = (phase_1, phase_2, phase_3, phase_4, phase_5, phase_6)

tested_by = 'E43'
test_date = 'I43'
