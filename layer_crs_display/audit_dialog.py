# SPDX-License-Identifier: GPL-2.0-or-later
"""On-demand, read-only CRS audit window."""

from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QBrush, QColor, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QVBoxLayout,
)
from qgis.core import QgsProject

from .audit_engine import scan_project
from .audit_logic import (
    STATUS_DIFFERENT,
    STATUS_MISSING,
    STATUS_OK,
    audit_summary,
    matches_filter,
    reprojectable_layer_ids,
)


STATUS_COLOURS = {
    STATUS_OK: ("#176d58", "#e5f3ed"),
    STATUS_DIFFERENT: ("#9a5b08", "#fff2d8"),
    STATUS_MISSING: ("#ad3737", "#fbe7e7"),
}


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class AuditDialog(QDialog):
    """Inspect project CRS consistency and hand selected rows to Batch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = QgsProject.instance()
        self.rows = []
        self.requested_layer_ids = []
        self.setObjectName("CrsAudit")
        self.setWindowTitle("CRS — Project Audit")
        self.setWindowIcon(
            QIcon(str(Path(__file__).with_name("audit_080.svg")))
        )
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.resize(920, 580)
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.resize(
                min(920, int(area.width() * 0.9)),
                min(580, int(area.height() * 0.85)),
            )
        self.setStyleSheet(
            """
            QDialog#CrsAudit { background: #f3f6fa; color: #233348; }
            QDialog#CrsAudit QWidget { color: #233348; }
            QFrame#card { background: #ffffff; border: 1px solid #d9e1eb;
                border-radius: 8px; }
            QLabel#heading { font-size: 19px; font-weight: 600; }
            QLabel#muted { color: #586a7e; }
            QLabel#summary { color: #245b88; font-size: 13px;
                font-weight: 600; }
            QComboBox { background: #ffffff; border: 1px solid #bac7d6;
                border-radius: 4px; padding: 5px; }
            QPushButton { background: #ffffff; border: 1px solid #b9c7d7;
                border-radius: 4px; padding: 6px 9px; }
            QPushButton:hover { background: #eaf1f8; border-color: #7195b7; }
            QPushButton#primary { background: #176d58; color: white;
                border-color: #176d58; font-weight: 600; }
            QPushButton#primary:hover { background: #125644; }
            QTableWidget { background: white; alternate-background-color: #f4f7fb;
                color: #233348; border: 1px solid #d9e1eb;
                gridline-color: #edf1f6; selection-background-color: #dceafb;
                selection-color: #183e62; }
            QHeaderView::section { background: #eaf0f7; color: #334e6a;
                border: none; border-right: 1px solid #d9e1eb; padding: 7px;
                font-weight: 600; }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        heading = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.windowIcon().pixmap(36, 36))
        heading.addWidget(icon)
        titles = QVBoxLayout()
        title = label("Project CRS audit")
        title.setObjectName("heading")
        titles.addWidget(title)
        subtitle = label(
            "Review layer CRS definitions against the current project CRS. "
            "This scan never changes project data or CRS assignments."
        )
        subtitle.setObjectName("muted")
        titles.addWidget(subtitle)
        heading.addLayout(titles, 1)
        outer.addLayout(heading)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        self.summary = label("")
        self.summary.setObjectName("summary")
        card_layout.addWidget(self.summary)

        controls = QHBoxLayout()
        controls.addWidget(label("Show"))
        self.status_filter = QComboBox()
        for value in ("All", STATUS_OK, STATUS_DIFFERENT, STATUS_MISSING):
            self.status_filter.addItem(value, value)
        self.status_filter.currentIndexChanged.connect(self.apply_filter)
        controls.addWidget(self.status_filter)
        controls.addStretch()
        self.select_different = QPushButton("Select Different")
        self.select_different.clicked.connect(self.select_different_rows)
        controls.addWidget(self.select_different)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        card_layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Status", "Layer", "CRS", "Type", "Datum", "Unit"]
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        for column, width in enumerate((90, 190, 125, 105, 230, 90)):
            self.table.setColumnWidth(column, width)
        card_layout.addWidget(self.table, 1)

        self.guidance = label(
            "Missing CRS cannot be reprojected. Assign the correct source CRS "
            "first, then refresh the audit."
        )
        self.guidance.setObjectName("muted")
        card_layout.addWidget(self.guidance)
        outer.addWidget(card, 1)

        footer = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        footer.addWidget(close_button)
        footer.addStretch()
        self.send_button = QPushButton("Send to Reproject")
        self.send_button.setObjectName("primary")
        self.send_button.clicked.connect(self.send_to_reproject)
        footer.addWidget(self.send_button)
        outer.addLayout(footer)
        self.refresh()

    def refresh(self):
        selected_ids = set(self.selected_layer_ids())
        self.rows = scan_project(self.project)
        self.table.clearSelection()
        self.table.setRowCount(len(self.rows))
        for row_index, row in enumerate(self.rows):
            values = (
                row["status"],
                row["name"],
                row["crs"] or "—",
                row["type"] or "—",
                row["datum"] or "—",
                row["unit"] or "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 0:
                    foreground, background = STATUS_COLOURS[row["status"]]
                    item.setForeground(QBrush(QColor(foreground)))
                    item.setBackground(QBrush(QColor(background)))
                self.table.setItem(row_index, column, item)
            if row["status"] == STATUS_MISSING:
                self.table.item(row_index, 0).setToolTip(
                    "CRS is not defined. Assign the correct source CRS before "
                    "reprojection."
                )
            if row["layer_id"] in selected_ids:
                self.table.setRangeSelected(
                    QTableWidgetSelectionRange(
                        row_index, 0, row_index, self.table.columnCount() - 1
                    ),
                    True,
                )

        counts = audit_summary(self.rows)
        self.summary.setText(
            "{layers} layers  •  {crs} CRS  •  {missing} Missing CRS  •  "
            "{different} Different from Project  •  Project: {project}".format(
                project=self.project.crs().authid()
                or self.project.crs().description()
                or "Not defined",
                **counts,
            )
        )
        self.apply_filter()
        self.send_button.setEnabled(bool(counts["different"]))

    def apply_filter(self, *args):
        selected = self.status_filter.currentData()
        for row_index, row in enumerate(self.rows):
            self.table.setRowHidden(
                row_index, not matches_filter(row, selected)
            )

    def select_different_rows(self):
        self.table.clearSelection()
        for row_index, row in enumerate(self.rows):
            if row["status"] == STATUS_DIFFERENT:
                self.table.setRangeSelected(
                    QTableWidgetSelectionRange(
                        row_index, 0, row_index, self.table.columnCount() - 1
                    ),
                    True,
                )

    def selected_layer_ids(self):
        indexes = self.table.selectionModel().selectedRows()
        return [
            self.rows[index.row()]["layer_id"]
            for index in sorted(indexes, key=lambda value: value.row())
            if index.row() < len(self.rows)
        ]

    def send_to_reproject(self):
        self.requested_layer_ids = reprojectable_layer_ids(
            self.rows, self.selected_layer_ids()
        )
        if not self.requested_layer_ids:
            QMessageBox.information(
                self,
                "CRS Audit",
                "Select at least one layer with Different status.",
            )
            return
        self.accept()
