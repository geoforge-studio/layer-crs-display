# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""QGIS entry point for Layer CRS Display."""


def classFactory(iface):
    """Return the plugin instance expected by QGIS."""
    from .plugin import LayerCrsDisplayPlugin

    return LayerCrsDisplayPlugin(iface)

