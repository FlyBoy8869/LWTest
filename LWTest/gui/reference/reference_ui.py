# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'reference_ui.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(354, 274)
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setObjectName("groupBox")
        self.widget = QtWidgets.QWidget(self.groupBox)
        self.widget.setGeometry(QtCore.QRect(10, 30, 127, 157))
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.reference_voltage_13800 = QtWidgets.QLineEdit(self.widget)
        self.reference_voltage_13800.setObjectName("reference_voltage_13800")
        self.verticalLayout.addWidget(self.reference_voltage_13800)
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.reference_current_13800 = QtWidgets.QLineEdit(self.widget)
        self.reference_current_13800.setObjectName("reference_current_13800")
        self.verticalLayout.addWidget(self.reference_current_13800)
        self.label_3 = QtWidgets.QLabel(self.widget)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.reference_power_13800 = QtWidgets.QLineEdit(self.widget)
        self.reference_power_13800.setObjectName("reference_power_13800")
        self.verticalLayout.addWidget(self.reference_power_13800)
        self.horizontalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_2.setObjectName("groupBox_2")
        self.widget1 = QtWidgets.QWidget(self.groupBox_2)
        self.widget1.setGeometry(QtCore.QRect(10, 30, 127, 157))
        self.widget1.setObjectName("widget1")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget1)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_4 = QtWidgets.QLabel(self.widget1)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_2.addWidget(self.label_4)
        self.reference_voltage_7200 = QtWidgets.QLineEdit(self.widget1)
        self.reference_voltage_7200.setObjectName("reference_voltage_7200")
        self.verticalLayout_2.addWidget(self.reference_voltage_7200)
        self.label_5 = QtWidgets.QLabel(self.widget1)
        self.label_5.setObjectName("label_5")
        self.verticalLayout_2.addWidget(self.label_5)
        self.reference_current_7200 = QtWidgets.QLineEdit(self.widget1)
        self.reference_current_7200.setObjectName("reference_current_7200")
        self.verticalLayout_2.addWidget(self.reference_current_7200)
        self.label_6 = QtWidgets.QLabel(self.widget1)
        self.label_6.setObjectName("label_6")
        self.verticalLayout_2.addWidget(self.label_6)
        self.reference_power_7200 = QtWidgets.QLineEdit(self.widget1)
        self.reference_power_7200.setObjectName("reference_power_7200")
        self.verticalLayout_2.addWidget(self.reference_power_7200)
        self.horizontalLayout.addWidget(self.groupBox_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_3.addWidget(self.buttonBox)
        self.verticalLayout_4.addLayout(self.verticalLayout_3)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "References"))
        self.groupBox.setTitle(_translate("Dialog", "13800KV Reference:"))
        self.label.setText(_translate("Dialog", "Voltage:"))
        self.label_2.setText(_translate("Dialog", "Current:"))
        self.label_3.setText(_translate("Dialog", "Power:"))
        self.groupBox_2.setTitle(_translate("Dialog", "7200KV Reference:"))
        self.label_4.setText(_translate("Dialog", "Voltage:"))
        self.label_5.setText(_translate("Dialog", "Current:"))
        self.label_6.setText(_translate("Dialog", "Power:"))