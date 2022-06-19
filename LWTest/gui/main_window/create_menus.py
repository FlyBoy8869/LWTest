from PyQt6.QtCore import Qt
from typing import Optional

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMainWindow, QMenu, QMenuBar


class MenuHelper:
    def __init__(self, parent, menu_bar: QMenuBar):
        self._parent = parent
        self._menu_bar = menu_bar

        self.menu_file: Optional[QMenu] = None
        self.menu_help: Optional[QMenu] = None

        self.action_configure_serial_numbers: Optional[QAction] = None
        self.action_create_set: Optional[QAction] = None
        self.action_enter_references: Optional[QAction] = None
        self.action_upgrade_sensor: Optional[QAction] = None
        self.action_advanced_configuration: Optional[QAction] = None
        # self.action_raw_config: Optional[QAction] = None
        self.action_save: Optional[QAction] = None
        self.action_exit: Optional[QAction] = None
        self.action_about: Optional[QAction] = None
        self.action_take_readings: Optional[QAction] = None
        self.action_config_correction_angle: Optional[QAction] = None
        self.action_fault_current: Optional[QAction] = None
        self.action_calibrate: Optional[QAction] = None
        self.action_check_persistence: Optional[QAction] = None

    def create_menus(self, window: QMainWindow):
        # create top level menus
        self.menu_file = self._menu_bar.addMenu("&File")
        self.menu_help = self._menu_bar.addMenu("&Help")

        # create actions
        action_name = [
            "create_set", "enter_references", "check_persistence",
            "configure_serial_numbers", "upgrade_sensor",
            "save", "exit",
            "about", "take_readings",
            "config_correction_angle", "fault_current",
            "calibrate", "advanced_configuration"
        ]
        action_icon = [
            None, None, None,
            "LWTest/resources/images/serial_config-01_128.png", "LWTest/resources/images/upgrade-01_128.png",
            "LWTest/resources/images/save-02_128.png", "LWTest/resources/images/exit-01_128.png",
            "LWTest/resources/images/info-01_128.png", "LWTest/resources/images/multimeter-01_128.png",
            "LWTest/resources/images/correction_angle.png", "LWTest/resources/images/fault_current-02.png",
            "LWTest/resources/images/calibrate.png", "LWTest/resources/images/advanced_configuration-01_128.png"
        ]
        action_text = [
            "Create Set", "Enter References", "Check\npersistence",
            "&Configure Serial Numbers", "&Upgrade firmware",
            "&Save", "E&xit",
            "&About", "Take Readings",
            "Set Correction Angle", "Fault Current",
            "Calibrate Sensor", "&Advanced Configuration"
        ]
        for name, icon, text in zip(action_name, action_icon, action_text):
            setattr(
                self,
                "".join(['action_', name]),
                QAction(QIcon(icon), text, window) if icon else QAction(text, window)
            )

        getattr(self, "action_check_persistence").setEnabled(False)

        # customize actions
        self.action_create_set.setShortcut(Qt.Key.Key_N | Qt.KeyboardModifier.ControlModifier.value)
        self.action_enter_references.setShortcut(Qt.Key.Key_R | Qt.KeyboardModifier.ControlModifier.value)
        self.action_save.setShortcut(Qt.Key.Key_S | Qt.KeyboardModifier.ControlModifier.value)
        self.action_upgrade_sensor.setShortcut(Qt.Key.Key_U | Qt.KeyboardModifier.ControlModifier.value)

        # add actions to menu
        self.menu_file.addAction(self.action_create_set)
        self.menu_file.addAction(self.action_enter_references)
        self.menu_file.addAction(self.action_upgrade_sensor)
        self.menu_file.addAction(self.action_save)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        self.menu_help.addAction(self.action_about)

        return self

    def connect_actions(self):
        """Automatically connect 'QAction.triggered' signals.

        For example, given a QAction named 'action_create_set', the parent widget must
        implement a handler of the following format:

            handle_action_create_set(checked: bool)

            or

            _handle_action_create_set(checked: bool)
        """
        actions = [k for k, v in self.__dict__.items() if isinstance(v, QAction)]
        methods = [e for e in dir(self._parent) if not e.startswith("__") and callable(getattr(self._parent, e))]

        for action in actions:
            for method in methods:
                # works whether the method or the action is marked as "private"
                if method.lstrip("_") == "handle_" + action.lstrip("_"):
                    a: QAction = getattr(self, action)
                    # noinspection PyUnresolvedReferences
                    a.triggered.connect(getattr(self._parent, method))
                    break

    @staticmethod
    def insert_spacer(toolbar, parent):
        spacer = QAction("  :  ", parent)
        spacer.setEnabled(False)
        toolbar.addAction(spacer)
