# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Main QGIS plugin implementation."""

from functools import partial
from pathlib import Path

from qgis.core import Qgis, QgsLayerTreeModel, QgsProject, QgsSettings
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import QSize, Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog

from .about_dialog import AboutDialog
from .crs_widget import PROVIDER_ID, CrsDisplayWidgetProvider
from .settings_dialog import SettingsDialog


PLUGIN_NAME = "Layer CRS Display"
PLUGIN_VERSION = "0.6.1"
SETTINGS_GROUP = "GeoForge/LayerCrsDisplay"


class LayerCrsDisplayPlugin:
    """Manage actions, settings and embedded CRS widgets."""

    def __init__(self, iface):
        self.iface = iface
        self.project = QgsProject.instance()
        self.provider = None
        self.toggle_action = None
        self.settings_action = None
        self.about_action = None
        self.batch_action = None
        self._batch_dialog = None
        self.toolbar = None
        self._layer_callbacks = {}
        self._signals_connected = False

    def initGui(self):  # noqa: N802 (QGIS API)
        self._register_provider()
        self._enable_embedded_widgets_flag()
        self._create_actions()
        self._connect_project_signals()

        for layer in self.project.mapLayers().values():
            self._connect_layer_signal(layer)

        if self.read_settings()["enabled"]:
            self._add_widgets_to_all_layers()

    def unload(self):
        if self._batch_dialog is not None and self._batch_dialog.runner.active:
            self._batch_dialog.runner.finished.connect(
                lambda *args: self._batch_dialog.reject()
            )
            self._batch_dialog.runner.cancel()
        self._disconnect_project_signals()
        self._disconnect_all_layer_signals()
        self._remove_widgets_from_all_layers()
        self._unregister_provider()
        self._remove_actions()

    # ------------------------------------------------------------------ GUI
    def _create_actions(self):
        enabled = self.read_settings()["enabled"]
        self.toggle_action = QAction(
            self._display_icon(enabled),
            "Display CRS",
            self.iface.mainWindow(),
        )
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(enabled)
        self.toggle_action.setToolTip(
            "Show or hide each layer's coordinate reference system in the "
            "Layers panel"
        )
        self.toggle_action.toggled.connect(self._on_toggle)

        self.settings_action = QAction(
            "Settings…", self.iface.mainWindow()
        )
        self.settings_action.triggered.connect(self.show_settings)

        self.about_action = QAction(
            "About…", self.iface.mainWindow()
        )
        self.about_action.triggered.connect(self.show_about)

        self.batch_action = QAction(
            QIcon(str(Path(__file__).with_name("reproject_061.svg"))),
            "Reproject",
            self.iface.mainWindow(),
        )
        self.batch_action.setToolTip(
            "Reproject selected layers to a target CRS using a shared output "
            "folder and name suffix"
        )
        self.batch_action.triggered.connect(self.show_batch)

        self.toolbar = self.iface.addToolBar("CRS")
        self.toolbar.setObjectName("GeoForgeLayerCrsToolbar")
        self.toolbar.setLayoutDirection(Qt.LeftToRight)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.setIconSize(QSize(28, 28))
        self.toolbar.setStyleSheet(
            """
            QToolButton {
                background: palette(button);
                border: 1px solid palette(mid);
                border-radius: 5px;
                margin: 2px;
                padding: 3px;
                min-width: 28px;
                min-height: 28px;
            }
            QToolButton:hover {
                background: palette(light);
                border-color: #7195b7;
            }
            QToolButton:checked {
                background: rgba(24, 119, 90, 45);
                border: 2px solid #18775a;
                padding: 2px;
            }
            QToolButton:pressed {
                background: rgba(36, 91, 136, 45);
                border-color: #245b88;
            }
            """
        )
        self.toolbar.addAction(self.toggle_action)
        self.toolbar.addAction(self.batch_action)
        self._configure_toolbar_button(
            self.toggle_action, "GeoForgeDisplayCrsButton"
        )
        self._configure_toolbar_button(
            self.batch_action, "GeoForgeReprojectButton"
        )
        self.toolbar.toolButtonStyleChanged.connect(
            self._keep_toolbar_icon_only
        )
        QTimer.singleShot(0, self._enforce_toolbar_button_style)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.toggle_action)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.batch_action)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.settings_action)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.about_action)

    def _display_icon(self, checked):
        filename = (
            "display_crs_on_061.svg"
            if checked
            else "display_crs_off_061.svg"
        )
        return QIcon(str(Path(__file__).with_name(filename)))

    def _update_display_icon(self, checked):
        if self.toggle_action is not None:
            self.toggle_action.setIcon(self._display_icon(checked))

    def _configure_toolbar_button(self, action, object_name):
        button = self.toolbar.widgetForAction(action)
        if button is not None:
            button.setObjectName(object_name)
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            button.setIconSize(QSize(28, 28))
            button.setAccessibleName(action.text())
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _enforce_toolbar_button_style(self):
        if self.toolbar is None:
            return
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._configure_toolbar_button(
            self.toggle_action, "GeoForgeDisplayCrsButton"
        )
        self._configure_toolbar_button(
            self.batch_action, "GeoForgeReprojectButton"
        )

    def _keep_toolbar_icon_only(self, style):
        if style != Qt.ToolButtonIconOnly:
            QTimer.singleShot(0, self._enforce_toolbar_button_style)

    def _remove_actions(self):
        for action in (
            self.toggle_action,
            self.settings_action,
            self.about_action,
            self.batch_action,
        ):
            if action is None:
                continue
            self.iface.removePluginMenu(PLUGIN_NAME, action)
            action.deleteLater()
        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

        self.toggle_action = None
        self.settings_action = None
        self.about_action = None
        self.batch_action = None

    def show_batch(self):
        from .batch_dialog import BatchDialog
        if self._batch_dialog is None:
            self._batch_dialog = BatchDialog(
                self.iface, self.iface.mainWindow()
            )
        elif not self._batch_dialog.runner.active:
            self._batch_dialog.refresh()
        self._batch_dialog.exec_()

    def show_settings(self):
        dialog = SettingsDialog(self.read_settings(), self.iface.mainWindow())
        if dialog.exec_() != QDialog.Accepted:
            return

        previous = self.read_settings()
        current = dialog.values()
        self.write_settings(current)

        self.toggle_action.blockSignals(True)
        self.toggle_action.setChecked(current["enabled"])
        self.toggle_action.blockSignals(False)
        self._update_display_icon(current["enabled"])

        if current["enabled"] and not previous["enabled"]:
            self._add_widgets_to_all_layers()
        elif not current["enabled"] and previous["enabled"]:
            self._remove_widgets_from_all_layers()
        elif current["enabled"]:
            self._refresh_all_widgets()

    def show_about(self):
        dialog = AboutDialog(PLUGIN_VERSION, self.iface.mainWindow())
        dialog.exec_()

    def _on_toggle(self, checked):
        self._update_display_icon(checked)
        settings = self.read_settings()
        settings["enabled"] = bool(checked)
        self.write_settings(settings)
        if checked:
            self._add_widgets_to_all_layers()
            message = "Layer CRS display enabled."
        else:
            self._remove_widgets_from_all_layers()
            message = "Layer CRS display disabled."
        self.iface.messageBar().pushMessage(
            PLUGIN_NAME, message, level=Qgis.Info, duration=3
        )

    # ------------------------------------------------------------- Settings
    def read_settings(self):
        settings = QgsSettings()
        display_format = settings.value(
            SETTINGS_GROUP + "/display_format", "authid", type=str
        )
        if display_format not in ("authid", "authid_name", "name"):
            display_format = "authid"
        return {
            "enabled": settings.value(
                SETTINGS_GROUP + "/enabled", True, type=bool
            ),
            "display_format": display_format,
        }

    def write_settings(self, values):
        settings = QgsSettings()
        settings.setValue(SETTINGS_GROUP + "/enabled", values["enabled"])
        settings.setValue(
            SETTINGS_GROUP + "/display_format", values["display_format"]
        )

    # --------------------------------------------------------------- Provider
    def _register_provider(self):
        registry = QgsGui.layerTreeEmbeddedWidgetRegistry()
        if PROVIDER_ID in registry.providers():
            registry.removeProvider(PROVIDER_ID)
        self.provider = CrsDisplayWidgetProvider(self.read_settings)
        if not registry.addProvider(self.provider):
            self.provider = None
            raise RuntimeError("Could not register the CRS widget provider")

    def _unregister_provider(self):
        registry = QgsGui.layerTreeEmbeddedWidgetRegistry()
        if PROVIDER_ID in registry.providers():
            registry.removeProvider(PROVIDER_ID)
        self.provider = None

    def _enable_embedded_widgets_flag(self):
        model = self.iface.layerTreeView().layerTreeModel()
        model.setFlag(QgsLayerTreeModel.UseEmbeddedWidgets, True)

    # --------------------------------------------------------------- Signals
    def _connect_project_signals(self):
        if self._signals_connected:
            return
        self.project.layersAdded.connect(self._on_layers_added)
        self.project.layersWillBeRemoved.connect(
            self._on_layers_will_be_removed
        )
        self._signals_connected = True

    def _disconnect_project_signals(self):
        if not self._signals_connected:
            return
        for signal, callback in (
            (self.project.layersAdded, self._on_layers_added),
            (
                self.project.layersWillBeRemoved,
                self._on_layers_will_be_removed,
            ),
        ):
            try:
                signal.disconnect(callback)
            except (TypeError, RuntimeError):
                pass
        self._signals_connected = False

    def _connect_layer_signal(self, layer):
        layer_id = layer.id()
        if layer_id in self._layer_callbacks:
            return
        callback = partial(self._refresh_layer_by_id, layer_id)
        try:
            layer.crsChanged.connect(callback)
            self._layer_callbacks[layer_id] = callback
        except (AttributeError, TypeError, RuntimeError):
            pass

    def _disconnect_layer_signal(self, layer_id):
        callback = self._layer_callbacks.pop(layer_id, None)
        layer = self.project.mapLayer(layer_id)
        if callback is None or layer is None:
            return
        try:
            layer.crsChanged.disconnect(callback)
        except (AttributeError, TypeError, RuntimeError):
            pass

    def _disconnect_all_layer_signals(self):
        for layer_id in list(self._layer_callbacks):
            self._disconnect_layer_signal(layer_id)
        self._layer_callbacks.clear()

    def _on_layers_added(self, layers):
        enabled = self.read_settings()["enabled"]
        for layer in layers:
            self._connect_layer_signal(layer)
            if enabled:
                self._add_widget_to_layer(layer)
                self._refresh_layer_by_id(layer.id())

    def _on_layers_will_be_removed(self, layer_ids):
        for layer_id in layer_ids:
            self._disconnect_layer_signal(layer_id)

    # --------------------------------------------------------------- Widgets
    @staticmethod
    def _embedded_widget_ids(layer):
        try:
            count = max(
                0, int(layer.customProperty("embeddedWidgets/count", 0))
            )
        except (TypeError, ValueError):
            count = 0
        return [
            str(
                layer.customProperty(
                    "embeddedWidgets/{}/id".format(index), ""
                )
            )
            for index in range(count)
        ]

    @staticmethod
    def _write_embedded_widget_ids(layer, provider_ids):
        try:
            old_count = max(
                0, int(layer.customProperty("embeddedWidgets/count", 0))
            )
        except (TypeError, ValueError):
            old_count = 0

        for index in range(old_count):
            layer.removeCustomProperty(
                "embeddedWidgets/{}/id".format(index)
            )

        provider_ids = [
            provider_id for provider_id in provider_ids if provider_id
        ]
        if provider_ids:
            layer.setCustomProperty("embeddedWidgets/count", len(provider_ids))
            for index, provider_id in enumerate(provider_ids):
                layer.setCustomProperty(
                    "embeddedWidgets/{}/id".format(index), provider_id
                )
        else:
            layer.removeCustomProperty("embeddedWidgets/count")

    def _add_widget_to_layer(self, layer):
        # Recognize pre-GeoForge provider namespaces in saved projects too.
        provider_ids = [
            provider_id
            for provider_id in self._embedded_widget_ids(layer)
            if not provider_id.endswith("_layer_crs_display")
        ]
        provider_ids.append(PROVIDER_ID)
        self._write_embedded_widget_ids(layer, provider_ids)

    def _remove_widget_from_layer(self, layer):
        provider_ids = [
            provider_id
            for provider_id in self._embedded_widget_ids(layer)
            if not provider_id.endswith("_layer_crs_display")
        ]
        self._write_embedded_widget_ids(layer, provider_ids)

    def _add_widgets_to_all_layers(self):
        for layer in self.project.mapLayers().values():
            self._connect_layer_signal(layer)
            self._add_widget_to_layer(layer)
        self._refresh_all_widgets()

    def _remove_widgets_from_all_layers(self):
        for layer in self.project.mapLayers().values():
            self._remove_widget_from_layer(layer)
        self._refresh_all_widgets()

    def _refresh_layer_by_id(self, layer_id):
        node = self.project.layerTreeRoot().findLayer(layer_id)
        if node is None:
            return
        try:
            model = self.iface.layerTreeView().layerTreeModel()
            model.refreshLayerLegend(node)
        except RuntimeError:
            pass

    def _refresh_all_widgets(self):
        for layer_id in self.project.mapLayers():
            self._refresh_layer_by_id(layer_id)
