# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""About dialog and official project links."""

from functools import partial
from pathlib import Path

from qgis.PyQt.QtCore import QSize, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


PLUGIN_LINKS = (
    (
        "QGIS plugin page",
        "https://plugins.qgis.org/plugins/layer_crs_display/",
        "qgisPluginPageLink",
    ),
    (
        "Source code",
        "https://github.com/geoforge-studio/layer-crs-display",
        "sourceCodeLink",
    ),
    (
        "Report an issue",
        "https://github.com/geoforge-studio/layer-crs-display/issues",
        "issueTrackerLink",
    ),
)

SOCIAL_LINKS = (
    (
        "LinkedIn",
        "https://www.linkedin.com/in/geoforge-studio-668319436",
        "linkedinLink",
        "linkedin.svg",
    ),
    (
        "Instagram",
        "https://www.instagram.com/geoforge_studio",
        "instagramLink",
        "instagram.svg",
    ),
    (
        "Telegram",
        "https://t.me/GeoforgeStudio",
        "telegramLink",
        "telegram.svg",
    ),
)

EMAIL_URL = "mailto:reynolds.mach88@gmail.com"


def _plain_label(text, object_name=""):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.PlainText)
    if object_name:
        widget.setObjectName(object_name)
    return widget


class AboutDialog(QDialog):
    """Present plugin information and verified GeoForge destinations."""

    def __init__(self, version, parent=None, url_opener=None):
        super().__init__(parent)
        self._url_opener = url_opener or QDesktopServices.openUrl

        self.setObjectName("LayerCrsAboutDialog")
        self.setWindowTitle("About Layer CRS Display")
        self.setWindowIcon(
            QIcon(str(Path(__file__).with_name("plugin_061.svg")))
        )
        self.setLayoutDirection(Qt.LeftToRight)
        self.setMinimumWidth(560)
        self.setStyleSheet(
            """
            QDialog#LayerCrsAboutDialog {
                background: #f3f6fa;
                color: #233348;
            }
            QDialog#LayerCrsAboutDialog QLabel { color: #233348; }
            QFrame#aboutCard {
                background: #ffffff;
                border: 1px solid #d9e1eb;
                border-radius: 8px;
            }
            QLabel#aboutTitle { font-size: 20px; font-weight: 600; }
            QLabel#aboutVersion { color: #176d58; font-weight: 600; }
            QLabel#aboutSection {
                color: #245b88;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#aboutMuted { color: #586a7e; }
            QPushButton {
                background: #ffffff;
                color: #233348;
                border: 1px solid #b9c7d7;
                border-radius: 4px;
                padding: 7px 10px;
                text-align: center;
            }
            QPushButton:hover {
                background: #eaf1f8;
                border-color: #7195b7;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(
            QIcon(str(Path(__file__).with_name("plugin_061.svg"))).pixmap(
                52, 52
            )
        )
        header.addWidget(icon, 0, Qt.AlignTop)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(_plain_label("Layer CRS Display", "aboutTitle"))
        heading.addWidget(
            _plain_label(
                "Version {}  |  QGIS 3".format(version), "aboutVersion"
            )
        )
        heading.addWidget(
            _plain_label(
                "Developed and maintained by GeoForge Studio", "aboutMuted"
            )
        )
        header.addLayout(heading, 1)
        root.addLayout(header)

        summary = _plain_label(
            "Display the coordinate reference system of every layer and batch "
            "reproject selected vector and raster layers without changing the "
            "source data."
        )
        root.addWidget(summary)

        links = self._card("Plugin resources")
        resource_grid = QGridLayout()
        resource_grid.setContentsMargins(0, 0, 0, 0)
        resource_grid.setHorizontalSpacing(8)
        for column, (caption, url, object_name) in enumerate(PLUGIN_LINKS):
            resource_grid.addWidget(
                self._link_button(caption, url, object_name), 0, column
            )
        links.layout().addLayout(resource_grid)

        links.layout().addWidget(
            _plain_label("Follow GeoForge Studio", "aboutSection")
        )
        social_grid = QGridLayout()
        social_grid.setContentsMargins(0, 0, 0, 0)
        social_grid.setHorizontalSpacing(8)
        social_destinations = SOCIAL_LINKS + (
            ("Email", EMAIL_URL, "emailLink", ""),
        )
        for column, (caption, url, object_name, icon_name) in enumerate(
            social_destinations
        ):
            social_grid.addWidget(
                self._link_button(
                    caption, url, object_name, icon_name=icon_name
                ),
                0,
                column,
            )
        links.layout().addLayout(social_grid)
        root.addWidget(links)

        note = _plain_label(
            "External links open in your default browser. GPL-2.0-or-later.",
            "aboutMuted",
        )
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _card(title):
        frame = QFrame()
        frame.setObjectName("aboutCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(_plain_label(title, "aboutSection"))
        return frame

    def _link_button(self, caption, url, object_name, icon_name=""):
        button = QPushButton(caption)
        button.setObjectName(object_name)
        button.setToolTip(url)
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setAutoDefault(False)
        if icon_name:
            button.setIcon(QIcon(str(Path(__file__).with_name(icon_name))))
            button.setIconSize(QSize(18, 18))
        button.clicked.connect(partial(self._open_url, url))
        return button

    def _open_url(self, url, _checked=False):
        self._url_opener(QUrl(url))
