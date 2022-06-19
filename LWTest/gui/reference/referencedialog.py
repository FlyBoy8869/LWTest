from collections import namedtuple

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog

from LWTest.gui.reference.reference_ui import Ui_Dialog


HighVoltageReference = namedtuple("HighVoltageReference", "voltage current power_factor, power")
LowVoltageReference = namedtuple("LowVoltageReference", "voltage current power_factor, power")


class ReferenceDialog(QDialog, Ui_Dialog):
    """Note: Currently the Power Factor reference is thrown away."""

    def __init__(self, parent, high_reference, low_reference):
        super().__init__(parent)
        self.setupUi(self)

        self.high_reference = high_reference
        self.low_reference = low_reference

        QTimer.singleShot(200, self._initialize_inputs)

    @property
    def high_voltage_reference(self):
        return HighVoltageReference(
            self.reference_voltage_13800.text(),
            self.reference_current_13800.text(),
            "0.9",
            self.reference_power_13800.text()
        )

    @property
    def low_voltage_reference(self):
        return LowVoltageReference(
            self.reference_voltage_7200.text(),
            self.reference_current_7200.text(),
            "0.9",
            self.reference_power_7200.text()
        )

    def _initialize_inputs(self):
        hv, hc, hpf, hp = self.high_reference
        self.reference_voltage_13800.setText(hv)
        self.reference_current_13800.setText(hc)
        self.reference_power_13800.setText(hp)

        lv, lc, lpf, lp = self.low_reference
        self.reference_voltage_7200.setText(lv)
        self.reference_current_7200.setText(lc)
        self.reference_power_7200.setText(lp)

        if not hv:
            self.reference_voltage_13800.setFocus()
        elif not hc:
            self.reference_current_13800.setFocus()
        elif not hp:
            self.reference_power_13800.setFocus()
        elif not lv:
            self.reference_voltage_7200.setFocus()
        elif not lc:
            self.reference_current_7200.setFocus()
        elif not lp:
            self.reference_power_7200.setFocus()
