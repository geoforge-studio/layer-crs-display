# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Settings dialog for Layer CRS Display."""

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Small dialog for the plugin's global settings."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Layer CRS Display settings")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)

        self.enabled_check = QCheckBox("Show CRS information for all layers")
        self.enabled_check.setChecked(settings["enabled"])
        root.addWidget(self.enabled_check)

        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItem("Authority ID only, e.g. EPSG:32639", "authid")
        self.format_combo.addItem("Authority ID and short CRS name", "authid_name")
        self.format_combo.addItem("CRS name only", "name")
        index = self.format_combo.findData(settings["display_format"])
        self.format_combo.setCurrentIndex(max(0, index))
        form.addRow("Display format:", self.format_combo)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self):
        return {
            "enabled": self.enabled_check.isChecked(),
            "display_format": self.format_combo.currentData(),
        }
