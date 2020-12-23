from enum import IntEnum, auto


class ReadingType(IntEnum):
    HIGH_VOLTAGE = auto()
    HIGH_CURRENT = auto()
    HIGH_POWER_FACTOR = auto()
    HIGH_REAL_POWER = auto()
    LOW_VOLTAGE = auto()
    LOW_CURRENT = auto()
    LOW_POWER_FACTOR = auto()
    LOW_REAL_POWER = auto()
    SCALE_CURRENT = auto()
    SCALE_VOLTAGE = auto()
    CORRECTION_ANGLE = auto()
    TEMPERATURE = auto()
    PERSISTS = auto()
    RSSI = auto()
    FIRMWARE = auto()
    REPORTING = auto()
    CALIBRATED = auto()
    FAULT_CURRENT = auto()


ADVANCED_CONFIG_SELECTOR = "div.tcell > input"
READING_SELECTOR = "div.tcellShort:not([id^='last'])"
