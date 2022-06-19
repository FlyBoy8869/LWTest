import darkdetect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

import LWTest.utilities.oscomp as oscomp


_alternate_row_color = QColor(Qt.GlobalColor.lightGray)

if oscomp.os_brand == oscomp.OSBrand.MAC and darkdetect.isDark():
    _alternate_row_color = QColor(45, 45, 45)

sensor_table_palette = QPalette()
sensor_table_palette.setColor(QPalette.ColorRole.AlternateBase, _alternate_row_color)
