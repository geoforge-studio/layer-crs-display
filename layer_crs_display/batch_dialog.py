# SPDX-License-Identifier: GPL-2.0-or-later
"""One scrollable dialog for CRS selection, output preview and batch progress."""
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor, QBrush
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QScrollArea, QLabel, QPushButton, QLineEdit, QFileDialog, QComboBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QMessageBox, QSizePolicy, QApplication, QFrame, QGridLayout, QToolButton)
from qgis.core import QgsProject, QgsSettings
from qgis.gui import QgsProjectionSelectionWidget

from .batch_engine import BatchRunner, eligibility, layer_kind
from .batch_logic import plan_outputs, output_names

SETTINGS = 'GeoForge/LayerCrsDisplay/batch/'


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.PlainText)
    return widget


class BatchDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.project = QgsProject.instance()
        self.setWindowTitle('CRS — Batch Reprojection')
        self.setLayoutDirection(Qt.LeftToRight)
        self.setMinimumSize(0, 0)
        self.resize(900, 620)
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.resize(min(900, int(area.width() * .9)), min(620, int(area.height() * .85)))
        self.runner = BatchRunner(self.project, self)
        self.runner.rowChanged.connect(self.on_row)
        self.runner.progressChanged.connect(lambda value: self.progress.setValue(round(value)))
        self.runner.finished.connect(self.on_finished)
        self.layer_ids = []
        self.auto_suffix = True
        self.refreshing = False
        self.manual_selection = False
        self.setObjectName('BatchReprojection')
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('convert.svg'))))
        self.setStyleSheet("""
            QDialog#BatchReprojection { background: #f3f6fa; color: #233348; }
            QDialog#BatchReprojection QWidget { color: #233348; }
            QFrame#card { background: #ffffff; border: 1px solid #d9e1eb; border-radius: 8px; }
            QLabel#heading { font-size: 19px; font-weight: 600; }
            QLabel#section { font-size: 13px; font-weight: 600; color: #245b88; }
            QLabel#muted { color: #586a7e; }
            QLabel#summary { color: #245b88; font-weight: 600; }
            QLineEdit, QComboBox { background: #ffffff; color: #233348;
                border: 1px solid #bac7d6; border-radius: 4px; padding: 5px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #2878ad; }
            QPushButton { background: #ffffff; border: 1px solid #b9c7d7;
                border-radius: 4px; padding: 6px 9px; }
            QPushButton:hover { background: #eaf1f8; border-color: #7195b7; }
            QDialog#BatchReprojection QPushButton#primary { background: #176d58; color: white; border-color: #176d58; font-weight: 600; }
            QDialog#BatchReprojection QPushButton#primary:hover { background: #125644; }
            QPushButton:disabled { background: #e7ecf2; color: #7b8794; border-color: #d2dbe4; }
            QDialog#BatchReprojection QPushButton#primary:disabled { background: #e7ecf2; color: #7b8794; border-color: #d2dbe4; }
            QTableWidget { background: white; alternate-background-color: #f4f7fb;
                color: #233348; border: 1px solid #d9e1eb; gridline-color: #edf1f6;
                selection-background-color: #dceafb; selection-color: #183e62; }
            QHeaderView::section { background: #eaf0f7; color: #334e6a;
                border: none; border-right: 1px solid #d9e1eb; padding: 7px; font-weight: 600; }
            QToolButton { background: transparent; border: none; padding: 6px; text-align: left; }
            QToolButton:hover { background: #e8eff6; }
            QProgressBar { background: #e1e8f0; border: none; border-radius: 3px;
                text-align: center; color: #233348; }
            QProgressBar::chunk { background: #7db7a4; border-radius: 3px; }
            QWidget#batchContent { background: #f3f6fa; }
            QScrollArea { border: none; background: transparent; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(0, 0)
        content = QWidget()
        content.setObjectName('batchContent')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QIcon(str(Path(__file__).with_name('convert.svg'))).pixmap(36, 36))
        heading.addWidget(icon)
        title = QVBoxLayout()
        title_text = label('Batch reprojection')
        title_text.setObjectName('heading')
        title.addWidget(title_text)
        subtitle = label('Bring your layers into one coordinate reference system.')
        subtitle.setObjectName('muted')
        title.addWidget(subtitle)
        heading.addLayout(title, 1)
        layout.addLayout(heading)

        def card(title_text):
            frame = QFrame()
            frame.setObjectName('card')
            box = QVBoxLayout(frame)
            box.setContentsMargins(14, 12, 14, 12)
            box.setSpacing(8)
            text = label(title_text)
            text.setObjectName('section')
            box.addWidget(text)
            layout.addWidget(frame)
            return frame, box

        self.controls, setup = card('1  Set the destination')
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setSpacing(10)
        self.target = QgsProjectionSelectionWidget()
        self.target.setCrs(self.project.crs())
        form.addRow('Target CRS', self.target)
        folder_box = QWidget()
        folder_layout = QHBoxLayout(folder_box)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        self.folder = QLineEdit(QgsSettings().value(SETTINGS + 'folder', '', type=str))
        self.folder.setMinimumWidth(0)
        self.folder.setPlaceholderText('Choose a folder for all outputs')
        self.folder.setClearButtonEnabled(True)
        browse = QPushButton('Browse…')
        browse.clicked.connect(self.browse)
        folder_layout.addWidget(self.folder, 1)
        folder_layout.addWidget(browse)
        form.addRow('Output folder', folder_box)
        self.suffix = QLineEdit()
        self.suffix.setPlaceholderText('_UTM39')
        self.suffix.setMinimumWidth(0)
        form.addRow('Name suffix', self.suffix)
        setup.addLayout(form)
        self.name_example = label('')
        self.name_example.setObjectName('muted')
        setup.addWidget(self.name_example)
        formats = label('Vector → GeoPackage    •    Raster → GeoTIFF\nOriginal files are kept. Existing outputs are never overwritten.')
        formats.setObjectName('muted')
        setup.addWidget(formats)

        _, layers_box = card('2  Choose the layers')
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search layer names or source CRS…')
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip('Filters the list only. Hidden checked layers are still included in the batch.')
        self.search.textChanged.connect(self.filter_rows)
        layers_box.addWidget(self.search)
        self.select_bar = QWidget()
        actions = QGridLayout(self.select_bar)
        actions.setContentsMargins(0, 0, 0, 0)
        for i, (text, callback) in enumerate([
            ('Select eligible', lambda: self.select('all')),
            ('Use panel selection', lambda: self.select('selected')),
            ('Clear selection', lambda: self.select('none')),
            ('Refresh layers', self.refresh)]):
            button = QPushButton(text)
            button.setToolTip('Applies to all layers, including layers hidden by the search filter.')
            button.clicked.connect(callback)
            actions.addWidget(button, i // 2, i % 2)
        layers_box.addWidget(self.select_bar)
        self.summary = label('')
        self.summary.setObjectName('summary')
        layers_box.addWidget(self.summary)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Use', 'Layer name', 'Source CRS', 'New layer name', 'Output file', 'Status'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumSize(0, 200)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        for col, width in enumerate((44, 160, 115, 175, 175, 250)):
            self.table.setColumnWidth(col, width)
        layers_box.addWidget(self.table)
        hint = label('Layers already in the target CRS are skipped. Check Status for any layer that cannot be selected.')
        hint.setObjectName('muted')
        layers_box.addWidget(hint)

        self.advanced_button = QToolButton()
        self.advanced_button.setText('Advanced options')
        self.advanced_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.advanced_button.setCheckable(True)
        self.advanced_button.setArrowType(Qt.RightArrow)
        layout.addWidget(self.advanced_button)
        self.options = QFrame()
        self.options.setObjectName('card')
        opts = QVBoxLayout(self.options)
        self.resampling = QComboBox()
        self.resampling.addItem('Nearest neighbour — categorical data', 0)
        self.resampling.addItem('Bilinear — continuous data', 1)
        self.resampling.addItem('Cubic — continuous data', 2)
        self.resampling.setMinimumContentsLength(12)
        self.resampling.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        opts.addWidget(label('Raster resampling'))
        opts.addWidget(self.resampling)
        self.add = QCheckBox('Add outputs to the project')
        self.add.setChecked(True)
        self.hide = QCheckBox('Hide originals after adding outputs')
        self.project_target = QCheckBox('Set project CRS to target')
        for w in (self.add, self.hide, self.project_target): opts.addWidget(w)
        self.add.toggled.connect(self.hide.setEnabled)
        opts.addWidget(label('Resampling applies to every raster in this batch. A shared CRS does not align raster grids. All features matching each layer filter are exported, regardless of feature selection.'))
        layout.addWidget(self.options)
        self.options.hide()
        self.advanced_button.toggled.connect(self.toggle_advanced)
        self.status = label('')
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.status)
        layout.addStretch()
        scroll.setWidget(content)
        self.scroll = scroll
        outer.addWidget(scroll, 1)

        # Persistent footer: execution controls never scroll out of view.
        self.footer_status = label('Choose an output folder to get started.')
        self.footer_status.setObjectName('muted')
        self.footer_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        outer.addWidget(self.footer_status)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.progress.setValue(0)
        outer.addWidget(self.progress)
        buttons = QHBoxLayout()
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.reject)
        self.cancel_button = QPushButton('Stop')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        self.run_button = QPushButton('Reproject')
        self.run_button.setObjectName('primary')
        self.run_button.setToolTip('Reproject all checked layers, including hidden search results')
        self.run_button.clicked.connect(self.run)
        for w in (self.close_button, self.cancel_button, self.run_button):
            w.setAutoDefault(False)
        buttons.addWidget(self.close_button)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.run_button)
        outer.addLayout(buttons)
        self.target.crsChanged.connect(self.target_changed)
        self.suffix.textEdited.connect(self.custom_suffix)
        self.suffix.textChanged.connect(self.preview)
        self.folder.textChanged.connect(self.preview)
        self.table.itemChanged.connect(self.selection_edited)
        self.target_changed()

    def toggle_advanced(self, expanded):
        self.options.setVisible(expanded)
        self.advanced_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

    def filter_rows(self, *args):
        query = self.search.text().strip().casefold()
        visible = 0
        checked = 0
        hidden_checked = 0
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, col) for col in (1, 2)]
            match = not query or any(query in item.text().casefold() for item in values if item)
            self.table.setRowHidden(row, not match)
            visible += int(match)
            selected = self.table.item(row, 0).checkState() == Qt.Checked
            checked += int(selected)
            hidden_checked += int(selected and not match)
        self.summary.setText('{} selected  •  {} of {} shown{}'.format(
            checked, visible, self.table.rowCount(),
            '  •  {} selected hidden by search'.format(hidden_checked) if hidden_checked else ''))

    def browse(self):
        path = QFileDialog.getExistingDirectory(self, 'Output folder', self.folder.text())
        if path: self.folder.setText(path)

    def custom_suffix(self, value):
        self.auto_suffix = False

    def target_changed(self):
        if self.auto_suffix:
            authid = self.target.crs().authid().replace(':', '')
            self.suffix.setText('_' + (authid or 'reprojected'))
        self.refresh()

    def refresh(self):
        if self.runner.active: return
        chosen = {key for row,key in enumerate(self.layer_ids) if self.table.item(row,0).checkState()==Qt.Checked}
        self.refreshing = True
        self.table.blockSignals(True)
        layers = []
        seen = set()
        for node in self.project.layerTreeRoot().findLayers():
            if node.layerId() not in seen and node.layer():
                layers.append(node.layer()); seen.add(node.layerId())
        self.layer_ids = [layer.id() for layer in layers]
        self.table.setRowCount(len(layers))
        for row, layer in enumerate(layers):
            problem = eligibility(layer, self.target.crs())
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable if not problem else Qt.NoItemFlags)
            check.setCheckState(Qt.Checked if not problem and (not self.manual_selection or layer.id() in chosen) else Qt.Unchecked)
            check.setData(Qt.UserRole, not bool(problem))
            self.table.setItem(row, 0, check)
            for col, text in ((1, layer.name()), (2, layer.crs().authid() or layer.crs().description()), (3, ''), (4, ''), (5, problem)):
                self.table.setItem(row, col, QTableWidgetItem(text))
        self.table.blockSignals(False)
        self.refreshing = False
        self.preview()
        self.filter_rows()

    def select(self, mode):
        self.manual_selection = True
        selected = {layer.id() for layer in self.iface.layerTreeView().selectedLayers()}
        self.table.blockSignals(True)
        for row, layer_id in enumerate(self.layer_ids):
            item = self.table.item(row, 0)
            if item.data(Qt.UserRole):
                item.setCheckState(Qt.Checked if mode=='all' or (mode=='selected' and layer_id in selected) else Qt.Unchecked)
        self.table.blockSignals(False)
        self.preview()
        self.filter_rows()

    def selection_edited(self, item):
        if not self.refreshing and not self.runner.active and item.column()==0:
            self.manual_selection = True
        self.preview()
        self.filter_rows()

    def selected_items(self):
        items = []
        for row, layer_id in enumerate(self.layer_ids):
            if self.table.item(row, 0).checkState() != Qt.Checked: continue
            layer = self.project.mapLayer(layer_id)
            if layer is None: raise ValueError('A layer has been removed. Refresh the list.')
            problem = eligibility(layer, self.target.crs())
            if problem: raise ValueError(layer.name() + ': ' + problem)
            items.append(dict(layer_id=layer_id, name=layer.name(), kind=layer_kind(layer), source_wkt=layer.crs().toWkt()))
        return items

    def preview(self, *args):
        if self.refreshing or self.runner.active: return
        self.table.blockSignals(True)
        try:
            plans = plan_outputs(self.selected_items(), self.folder.text(), self.suffix.text())
            by_id = {p['layer_id']:p for p in plans}
            for row, layer_id in enumerate(self.layer_ids):
                plan = by_id.get(layer_id)
                if plan:
                    for col, text in ((3,plan['output_name']),(4,plan['filename']),(5,plan['error'] or 'Ready')):
                        self.table.item(row,col).setText(text)
                        if col == 5:
                            self.table.item(row,col).setForeground(QBrush(QColor('#ad3737' if plan['error'] else '#176d58')))
                        self.table.item(row,col).setToolTip(plan['output_path'] if col==4 else text)
                elif self.table.item(row,0).data(Qt.UserRole):
                    for col in (3,4): self.table.item(row,col).setText('')
                    self.table.item(row,5).setText('Not selected')
            ready = bool(plans) and self.target.crs().isValid() and bool(self.folder.text().strip()) and Path(self.folder.text()).is_dir() and not any(p['error'] for p in plans)
            self.run_button.setEnabled(ready)
            self.name_example.setText('Example: Roads → Roads' + self.suffix.text())
            if not self.target.crs().isValid():
                message = 'Choose a valid target CRS.'
            elif not plans:
                message = 'Select at least one eligible layer.'
            elif not self.folder.text().strip() or not Path(self.folder.text()).is_dir():
                message = 'Choose a valid output folder.'
            elif any(p['error'] for p in plans):
                message = 'Resolve the output name conflicts shown in Status.'
            else:
                message = 'Ready to reproject {} layer(s).'.format(len(plans))
            self.status.setText(message)
            self.footer_status.setText(message)
        except Exception as exc:
            self.run_button.setEnabled(False)
            self.status.setText(str(exc))
            self.footer_status.setText('Check the settings. Details are shown above.')
        finally:
            self.table.blockSignals(False)
            self.filter_rows()

    def run(self):
        try:
            plans = plan_outputs(self.selected_items(), self.folder.text(), self.suffix.text())
            if not Path(self.folder.text()).is_dir(): raise ValueError('Choose a valid output folder.')
            QgsSettings().setValue(SETTINGS+'folder', self.folder.text())
            self.runner.start(plans,self.target.crs(),self.resampling.currentData(),self.add.isChecked(),self.hide.isChecked(),self.project_target.isChecked())
            self.busy(True)
            self.progress.setValue(0)
        except Exception as exc:
            QMessageBox.warning(self,'CRS Reprojection',str(exc))

    def busy(self, value):
        for w in (self.controls,self.select_bar,self.table,self.options,self.close_button,self.advanced_button): w.setEnabled(not value)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(value)
        if value: self.footer_status.setText('Reprojecting… You can stop the batch at any time.')

    def cancel(self):
        self.runner.cancel()
        self.cancel_button.setEnabled(False)
        self.status.setText('Stopping… Completed outputs will be retained.')
        self.footer_status.setText('Stopping… Completed outputs are kept.')

    def on_row(self, layer_id, status, text):
        if layer_id in self.layer_ids:
            item = self.table.item(self.layer_ids.index(layer_id),5)
            item.setText(text)
            item.setToolTip(text)
            item.setForeground(QBrush(QColor({'success':'#176d58', 'failed':'#ad3737', 'running':'#245b88'}.get(status, '#586a7e'))))

    def on_finished(self, results, report):
        self.busy(False)
        counts = {key:sum(r['status']==key for r in results) for key in ('success','failed','cancelled')}
        self.footer_status.setText('{success} succeeded • {failed} failed • {cancelled} cancelled'.format(**counts))
        self.status.setText('Succeeded: {success} | Failed: {failed} | Cancelled: {cancelled}\nReport: '.format(**counts)+report+'\nClick Refresh before starting another batch.')
        self.run_button.setEnabled(False)

    def reject(self):
        if self.runner.active:
            self.status.setText('Click Stop and wait for the current reprojection to finish.')
            return
        super().reject()

    def closeEvent(self, event):
        if self.runner.active:
            event.ignore()
            self.reject()
        else: event.accept()
