import enum
import platform

from PyQt5.QtCore import QSettings


class OSType(enum.Enum):
    LINUX = "Linux"
    MAC = "Darwin"
    WINDOWS = "Windows"


_os_map = {"Darwin": OSType.MAC, "Linux": OSType.LINUX, "Windows": OSType.WINDOWS}
os_type = _os_map[platform.system()]


class QSettingsAdapter:
    """This class hides the type differences between Windows and macOS."""

    @staticmethod
    def value(key):
        """Returns the value associated with 'key'. If 'key' contents is equal to True or False, a lower cased
        string representation is returned instead e.g., 'true' or 'false'."""
        result = str(QSettings().value(key, None))
        if (lc := result.lower()) in ["true", "false"]:
            return lc

        return result

    @staticmethod
    def set_value(key, value):
        QSettings().setValue(key, value)
