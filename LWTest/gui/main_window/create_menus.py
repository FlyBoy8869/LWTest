from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMenu, QAction, QMenuBar


class MenuHelper:
    def __init__(self, menu_bar: QMenuBar):
        self.menu_bar = menu_bar

        self.menu_file: Optional[QMenu] = None
        self.menu_help: Optional[QMenu] = None

        self.action_configure: Optional[QAction] = None
        self.action_upgrade: Optional[QAction] = None
        self.action_advanced_configuration: Optional[QAction] = None
        self.action_raw_config: Optional[QAction] = None
        self.action_save: Optional[QAction] = None
        self.action_exit: Optional[QAction] = None
        self.action_about: Optional[QAction] = None
        self.action_take_readings: Optional[QAction] = None
        self.action_config_correction_angle: Optional[QAction] = None
        self.action_fault_current: Optional[QAction] = None
        self.action_calibrate: Optional[QAction] = None
        self.action_check_persistence: Optional[QAction] = None

        self.actions = None
        self.actions_enabled = 0

    def create_menus(self, window: QMainWindow):
        # create top level menus
        self.menu_file = self.menu_bar.addMenu("&File")
        self.menu_help = self.menu_bar.addMenu("&Help")

        # create actions
        self.action_advanced_configuration = QAction(QIcon("LWTest/resources/images/advanced_configuration-01_128.png"),
                                                     "&Advanced Configuration", window)

        self.action_configure = QAction(QIcon("LWTest/resources/images/serial_config-01_128.png"),
                                        "&Configure Serial Numbers", window)

        self.action_upgrade = QAction(QIcon("LWTest/resources/images/upgrade-01_128.png"), "&Upgrade firmware", window)

        self.action_save = QAction(QIcon("LWTest/resources/images/save-02_128.png"), "&Save", window)

        self.action_exit = QAction(QIcon("LWTest/resources/images/exit-01_128.png"), "E&xit", window)
        self.action_exit.triggered.connect(window.close)

        self.action_about = QAction(QIcon("LWTest/resources/images/info-01_128.png"), "&About", window)

        self.action_take_readings = QAction(QIcon("LWTest/resources/images/multimeter-01_128.png"), "Take Readings",
                                            window)

        self.action_config_correction_angle = QAction(QIcon('LWTest/resources/images/correction_angle.png'),
                                                      "Set Correction Angle", window)

        self.action_fault_current = QAction(QIcon("LWTest/resources/images/fault_current-02.png"),
                                            "Fault Current", window)

        self.action_calibrate = QAction(QIcon("LWTest/resources/images/calibrate.png"), "Calibrate Sensor", window)

        self.action_check_persistence = QAction("Check\npersistence", window)
        self.action_check_persistence.setEnabled(False)

        # add actions to menu
        self.menu_file.addAction(self.action_upgrade)
        self.menu_file.addAction(self.action_save)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        self.menu_help.addAction(self.action_about)

        self.actions = [self.action_upgrade, self.action_advanced_configuration,
                        self.action_calibrate, self.action_config_correction_angle,
                        self.action_take_readings, self.action_check_persistence, self.action_fault_current]

        return self

    @staticmethod
    def insert_spacer(toolbar, parent):
        spacer = QAction("  :  ", parent)
        spacer.setEnabled(False)
        toolbar.addAction(spacer)
