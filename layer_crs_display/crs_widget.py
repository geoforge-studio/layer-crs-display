# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Embedded layer-tree widget for showing layer CRS information."""

from qgis.gui import QgsLayerTreeEmbeddedWidgetProvider
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from .formatting import display_text, tooltip_html


PROVIDER_ID = "geoforge_layer_crs_display"


class CrsDisplayWidget(QWidget):
    """A compact CRS badge shown before a layer's legend entries."""

    def __init__(self, layer, settings_reader, parent=None):
        super().__init__(parent)
        self._layer = layer
        self._settings_reader = settings_reader

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMaximumHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 1)
        layout.setSpacing(0)
        layout.addStretch(1)

        self.label = QLabel(self)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setLayoutDirection(Qt.LeftToRight)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.label, 0)

        self.refresh()

    def refresh(self):
        """Read the current layer CRS and refresh the badge."""
        settings = self._settings_reader()
        layer_crs = self._layer.crs()

        layer_valid = bool(layer_crs and layer_crs.isValid())
        layer_auth = layer_crs.authid() if layer_valid else ""
        layer_name = layer_crs.description() if layer_valid else ""

        self.label.setText(
            display_text(layer_auth, layer_name, settings["display_format"])
        )
        self.label.setToolTip(
            tooltip_html(
                self._layer.name(),
                layer_auth,
                layer_name,
            )
        )
        self._apply_style(layer_valid)

    def _apply_style(self, layer_valid):
        if layer_valid:
            style = (
                "color: palette(text); background-color: rgba(127, 127, 127, 28); "
                "border: 1px solid rgba(127, 127, 127, 70);"
            )
        else:
            style = (
                "color: #A31515; background-color: #FDECEC; "
                "border: 1px solid #E6A0A0;"
            )
        self.label.setStyleSheet(
            "QLabel {{ padding: 1px 6px; border-radius: 7px; {} }}".format(
                style
            )
        )


class CrsDisplayWidgetProvider(QgsLayerTreeEmbeddedWidgetProvider):
    """Factory registered with QGIS for the embedded CRS badge."""

    def __init__(self, settings_reader):
        super().__init__()
        self._settings_reader = settings_reader

    def id(self):
        return PROVIDER_ID

    def name(self):
        return "Layer CRS display"

    def createWidget(self, layer, widgetIndex):  # noqa: N802 (QGIS API)
        del widgetIndex
        return CrsDisplayWidget(layer, self._settings_reader)

    def supportsLayer(self, layer):  # noqa: N802 (QGIS API)
        return layer is not None and hasattr(layer, "crs")
