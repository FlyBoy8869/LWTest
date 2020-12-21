from PyQt5.QtWidgets import QDialog

from LWTest.gui.reference.referencedialog import ReferenceDialog


class GetReferences:
    def __init__(self, parent, high_refs, low_refs):
        self._parent = parent
        self._high_refs = high_refs
        self._low_refs = low_refs

    def get_references(self):
        reference_dialog = ReferenceDialog(self._parent, self._high_refs, self._low_refs)
        if reference_dialog.exec() == QDialog.Accepted:
            return reference_dialog.high_voltage_reference, reference_dialog.low_voltage_reference

        return None, None
