# SPDX-License-Identifier: GPL-2.0-or-later
"""Sequential Processing tasks with private staging and final-only outputs."""
import math
import os
import shutil
import tempfile
from pathlib import Path

from qgis.PyQt.QtCore import QObject, pyqtSignal, QTimer
from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsProcessingAlgRunnerTask,
    QgsProcessingContext, QgsProcessingFeedback, QgsFeatureRequest, QgsVectorLayer,
    QgsRasterLayer, QgsMapLayerStyle)
from .batch_logic import SIDECARS, publish_file


_invalid_geometry_enum = getattr(Qgis, 'InvalidGeometryCheck', None)
if _invalid_geometry_enum is not None:
    GEOMETRY_ABORT_ON_INVALID = getattr(
        _invalid_geometry_enum, 'AbortOnInvalid'
    )
else:  # QGIS 3.22 compatibility
    GEOMETRY_ABORT_ON_INVALID = getattr(
        QgsFeatureRequest, 'GeometryAbortOnInvalid'
    )


def same_crs(source, target):
    """Compare complete CRS definitions, including aliases, without losing epochs."""
    if not source.isValid() or not target.isValid():
        return False
    epochs = [getattr(crs, 'coordinateEpoch', lambda: float('nan'))() for crs in (source, target)]
    if not (all(math.isnan(e) for e in epochs) or epochs[0] == epochs[1]):
        return False
    if source == target:
        return True
    try:
        from osgeo import osr
        a, b = osr.SpatialReference(), osr.SpatialReference()
        if a.ImportFromWkt(source.toWkt()) or b.ImportFromWkt(target.toWkt()):
            return False
        # QGIS layer coordinates use traditional GIS x/y order.
        a.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        b.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        return bool(a.IsSame(b))
    except (ImportError, RuntimeError, AttributeError):
        return False


class ConversionFeedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.errors = []

    def reportError(self, error, fatalError=False):
        self.errors.append(str(error))
        super().reportError(error, fatalError)


def layer_kind(layer):
    if isinstance(layer, QgsVectorLayer):
        return 'vector' if layer.isSpatial() else ''
    if isinstance(layer, QgsRasterLayer) and layer.providerType() == 'gdal':
        return 'raster'
    return ''


def eligibility(layer, target):
    if layer is None or not layer.isValid():
        return 'The layer is invalid or has been removed.'
    if not layer_kind(layer):
        return 'Only spatial vector layers and GDAL-readable rasters are supported.'
    if not layer.crs().isValid():
        return 'Unknown source CRS. Assign the actual source CRS before reprojection.'
    if same_crs(layer.crs(), target):
        return 'Already in the target CRS.'
    if isinstance(layer, QgsVectorLayer) and layer.isEditable():
        return 'Save changes and leave layer edit mode first.'
    return ''


class BatchRunner(QObject):
    rowChanged = pyqtSignal(str, str, str)
    progressChanged = pyqtSignal(float)
    finished = pyqtSignal(object, str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.active = False
        self.task = None
        self.context = None
        self.feedback = None
        self.results = []
        self._retired_tasks = []
        self.stage = None
        self.pending_vectors = []
        self.package_stage = None
        self.package_layers = []

    def start(self, plans, target, resampling=0, add_layers=True, hide_sources=False, project_crs=False):
        if self.active:
            raise ValueError('The previous reprojection is still running.')
        if not target.isValid() or not plans:
            raise ValueError('A valid target CRS and at least one layer are required.')
        self.plans = [dict(p) for p in plans]
        if any(p.get('error') for p in plans):
            raise ValueError('Resolve output name errors before starting.')
        vectors = [p for p in plans if p['kind'] == 'vector']
        if vectors and (len({p['output_path'] for p in vectors}) != 1 or
                        any(not p.get('output_layer') for p in vectors)):
            raise ValueError('Vector outputs must use one GeoPackage with named layers. Refresh the preview.')
        self.target = QgsCoordinateReferenceSystem(target)
        self._retired_tasks.clear()
        self.resampling = resampling
        self.add_layers, self.hide_sources, self.set_project_crs = add_layers, hide_sources, project_crs
        self.cancelled = False
        self.active = True
        self.index = 0
        self.results = []
        self.pending_vectors = []
        self.package_layers = []
        self.package_stage = None
        self.packaging = False
        self.has_vectors = bool(vectors)
        QTimer.singleShot(0, self._next)

    def cancel(self):
        self.cancelled = True
        if self.feedback:
            self.feedback.cancel()
        if self.task:
            self.task.cancel()

    def _next(self):
        if self.index >= len(self.plans) or self.cancelled:
            for p in self.plans[self.index:]:
                self._record(p, 'cancelled', 'Not processed: operation cancelled.')
            if self.pending_vectors and not self.cancelled:
                self._package_vectors()
            else:
                for entry in self.pending_vectors:
                    self._record(entry['plan'], 'cancelled', 'Cancelled before the shared GeoPackage was saved.')
                self._finish()
            return
        self.current = self.plans[self.index]
        self.stage = None
        layer = self.project.mapLayer(self.current['layer_id'])
        self.current_layer = layer
        try:
            if layer is not None and layer.isValid() and same_crs(layer.crs(), self.target):
                self._record(self.current, 'skipped', 'Already in the target CRS; no copy created.')
                self.index += 1
                QTimer.singleShot(0, self._next)
                return
            problem = eligibility(layer, self.target)
            if problem:
                raise ValueError(problem)
            if layer.crs().toWkt() != self.current['source_wkt']:
                raise ValueError('The source CRS changed after selection. Refresh the layer list.')
            if layer.name() != self.current['name']:
                raise ValueError('The layer name changed after selection. Refresh the layer list.')
            path = Path(self.current['output_path'])
            if path.exists():
                raise ValueError('The output file already exists. Existing files will not be overwritten.')
            self.stage = Path(
                tempfile.mkdtemp(prefix='geoforge_crs_stage_')
            )
            self.staged_file = self.stage / path.name
            self.style = QgsMapLayerStyle()
            self.style.readFromLayer(layer)
            self.context = QgsProcessingContext()
            self.context.setProject(self.project)
            self.context.setTransformContext(self.project.transformContext())
            self.context.setInvalidGeometryCheck(GEOMETRY_ABORT_ON_INVALID)
            self.feedback = ConversionFeedback()
            self.feedback.progressChanged.connect(self._progress)
            self.current['subset_filter'] = layer.subsetString() if isinstance(layer, QgsVectorLayer) else ''
            self.current['source_crs'] = layer.crs().authid() or layer.crs().description()
            algorithm_id = 'native:reprojectlayer' if self.current['kind'] == 'vector' else 'gdal:warpreproject'
            algorithm = QgsApplication.processingRegistry().algorithmById(algorithm_id)
            if algorithm is None:
                raise ValueError('Algorithm {} is unavailable. Enable Processing and the GDAL provider.'.format(algorithm_id))
            params = dict(INPUT=layer, TARGET_CRS=self.target, OUTPUT=str(self.staged_file))
            if self.current['kind'] == 'raster':
                params.update(SOURCE_CRS=layer.crs(), RESAMPLING=self.resampling, DATA_TYPE=0,
                    MULTITHREADING=True, OPTIONS='TILED=YES|BIGTIFF=IF_SAFER',
                    EXTRA='-wo NUM_THREADS={}'.format(min(4, max(1, os.cpu_count() or 1))))
            self.task = QgsProcessingAlgRunnerTask(algorithm, params, self.context, self.feedback)
            self.task.setDependentLayers([layer])
            self.task.executed.connect(self._done)
            self.rowChanged.emit(self.current['layer_id'], 'running', 'Reprojecting…')
            QgsApplication.taskManager().addTask(self.task)
        except Exception as exc:
            self._record(self.current, 'failed', str(exc))
            self._cleanup()
            self.index += 1
            QTimer.singleShot(0, self._next)

    def _progress(self, value):
        if self.packaging:
            self.progressChanged.emit(90 + value / 10)
        else:
            self.progressChanged.emit((90 if self.has_vectors else 100) * (self.index + value / 100) / len(self.plans))

    def _done(self, successful, results):
        """QgsProcessingAlgRunnerTask emits executed from its main-thread finished()."""
        try:
            if self.cancelled or self.task.isCanceled():
                self._record(self.current, 'cancelled', 'Cancelled. No incomplete output was published.')
            elif not successful or self.feedback.errors:
                raise ValueError('\n'.join(self.feedback.errors) or self.feedback.textLog() or 'The reprojection algorithm failed.')
            else:
                self._publish()
        except Exception as exc:
            self._record(self.current, 'failed', str(exc))
        finally:
            self._cleanup()
            self.index += 1
            self._progress(0)
            QTimer.singleShot(0, self._next)

    def _publish(self):
        kind, name = self.current['kind'], self.current['output_name']
        def load(path):
            if kind == 'vector':
                return QgsVectorLayer(str(path), name, 'ogr')
            return QgsRasterLayer(str(path), name, 'gdal')

        check = load(self.staged_file)
        if not check.isValid() or check.crs() != self.target:
            raise ValueError('No valid output in the target CRS was produced.')
        if kind == 'vector':
            count = check.featureCount()
            # A count is queried only after conversion, when providers usually cache it.
            expected = self.current_layer.featureCount()
            if expected >= 0 and count != expected:
                raise ValueError('The output feature count differs from the filtered source layer.')
            self.current['output_features'] = count
            check = None
            self.pending_vectors.append(dict(plan=dict(self.current), path=self.staged_file,
                                             stage=self.stage, style=self.style))
            self.stage = None  # Keep the converted source until packaging completes.
            self._record(self.current, 'staged', 'Converted; waiting for the shared GeoPackage.')
            return
        check = None  # Release file handles before rename on Windows.
        final = Path(self.current['output_path'])
        if any(Path(str(final)+suffix).exists() for suffix in SIDECARS):
            raise ValueError('A sidecar file already exists in the destination. Output publication was stopped.')
        # Reserve the final pathname with O_EXCL: never overwrite an existing file.
        publish_file(self.staged_file, final)
        # Common raster sidecars, if the provider created them.
        warnings = []
        for suffix in ('.aux.xml', '.ovr', '.msk'):
            source = Path(str(self.staged_file) + suffix)
            if source.exists():
                destination = Path(str(final) + suffix)
                try:
                    with destination.open('xb') as stream, source.open('rb') as original:
                        shutil.copyfileobj(original, stream)
                except Exception as exc:
                    warnings.append('Could not transfer a sidecar file: ' + str(exc))
        if self.add_layers:
            output = load(final)
            if not output.isValid():
                warnings.append('The file was saved but could not be added to the project.')
            else:
                try:
                    self.style.writeToLayer(output)
                except Exception:
                    warnings.append('The layer style could not be transferred.')
                # Style XML must never reassign the output CRS.
                if output.crs() != self.target:
                    warnings.append('The style was not applied because it was incompatible with the target CRS.')
                    output = load(final)
                output.setName(name)
                self.project.addMapLayer(output)
                if self.hide_sources:
                    node = self.project.layerTreeRoot().findLayer(self.current['layer_id'])
                    if node:
                        node.setItemVisibilityChecked(False)
        self._record(self.current, 'success', 'Saved.' + ('\n' + '\n'.join(warnings) if warnings else ''))

    def _record(self, plan, status, message):
        result = dict(plan, status=status, message=message)
        for index, previous in enumerate(self.results):
            if previous['layer_id'] == plan['layer_id']:
                self.results[index] = result
                break
        else:
            self.results.append(result)
        self.rowChanged.emit(plan['layer_id'], status, message)

    def _package_vectors(self):
        """Package only validated converted layers, in one background task."""
        try:
            final = Path(self.pending_vectors[0]['plan']['output_path'])
            if final.exists() or any(Path(str(final)+s).exists() for s in SIDECARS):
                raise ValueError('The destination GeoPackage or a sidecar already exists.')
            self.package_stage = Path(
                tempfile.mkdtemp(prefix='geoforge_crs_stage_')
            )
            self.package_file = self.package_stage / final.name
            for entry in self.pending_vectors:
                layer = QgsVectorLayer(str(entry['path']), entry['plan']['output_layer'], 'ogr')
                if not layer.isValid():
                    raise ValueError('A converted layer could not be reopened for packaging.')
                self.package_layers.append(layer)
            algorithm = QgsApplication.processingRegistry().algorithmById('native:package')
            if algorithm is None:
                raise ValueError('The Package layers algorithm is unavailable. Enable Processing.')
            self.context = QgsProcessingContext()
            self.context.setProject(self.project)
            self.context.setTransformContext(self.project.transformContext())
            self.feedback = ConversionFeedback()
            self.packaging = True
            self.feedback.progressChanged.connect(self._progress)
            params = dict(LAYERS=self.package_layers, OUTPUT=str(self.package_file),
                          OVERWRITE=False, SAVE_STYLES=False, SAVE_METADATA=False,
                          SELECTED_FEATURES_ONLY=False, EXPORT_RELATED_LAYERS=False)
            self.task = QgsProcessingAlgRunnerTask(algorithm, params, self.context, self.feedback)
            self.task.setDependentLayers(self.package_layers)
            self.task.executed.connect(self._package_done)
            for entry in self.pending_vectors:
                self.rowChanged.emit(entry['plan']['layer_id'], 'packaging', 'Saving shared GeoPackage…')
            QgsApplication.taskManager().addTask(self.task)
        except Exception as exc:
            for entry in self.pending_vectors:
                self._record(entry['plan'], 'failed', str(exc))
            self._cleanup()
            self._finish()

    def _package_done(self, successful, results):
        check = None
        try:
            if self.cancelled or self.task.isCanceled():
                for entry in self.pending_vectors:
                    self._record(entry['plan'], 'cancelled', 'Cancelled; no partial GeoPackage was published.')
            elif not successful or self.feedback.errors:
                raise ValueError('\n'.join(self.feedback.errors) or 'Shared GeoPackage creation failed.')
            else:
                final = Path(self.pending_vectors[0]['plan']['output_path'])
                for entry in self.pending_vectors:
                    plan = entry['plan']
                    uri = str(self.package_file) + '|layername=' + plan['output_layer']
                    check = QgsVectorLayer(uri, plan['output_name'], 'ogr')
                    if (not check.isValid() or check.crs() != self.target or
                            check.featureCount() != plan['output_features']):
                        raise ValueError('Shared GeoPackage validation failed for ' + plan['output_name'])
                    check = None
                if any(Path(str(final)+s).exists() for s in SIDECARS):
                    raise ValueError('A destination sidecar appeared while processing. Nothing was overwritten.')
                publish_file(self.package_file, final)
                for entry in self.pending_vectors:
                    plan = entry['plan']
                    plan['output_uri'] = str(final) + '|layername=' + plan['output_layer']
                    warning = ''
                    if self.add_layers:
                        try:
                            output = QgsVectorLayer(plan['output_uri'], plan['output_name'], 'ogr')
                            if not output.isValid():
                                raise ValueError('Could not load the saved layer.')
                            entry['style'].writeToLayer(output)
                            if output.crs() != self.target:
                                output = QgsVectorLayer(plan['output_uri'], plan['output_name'], 'ogr')
                            output.setName(plan['output_name'])
                            self.project.addMapLayer(output)
                            if self.hide_sources:
                                node = self.project.layerTreeRoot().findLayer(plan['layer_id'])
                                if node:
                                    node.setItemVisibilityChecked(False)
                        except Exception as exc:
                            warning = ' Project/style update failed: ' + str(exc)
                    self._record(plan, 'success', 'Saved to shared GeoPackage.' + warning)
        except Exception as exc:
            for entry in self.pending_vectors:
                self._record(entry['plan'], 'failed', str(exc))
        finally:
            check = None  # Release a failed validation handle before cleanup on Windows.
            self._cleanup()
            self._finish()

    def _cleanup(self):
        if self.task:
            # Keep context/feedback alive through the task's finished callback.
            self._retired_tasks.append((self.task, self.context, self.feedback))
        if self.stage:
            self._remove_stage(self.stage)
            self.stage = None
        self.task = None
        self.feedback = None
        self.context = None
        self.current_layer = None

    def _remove_stage(self, path, attempt=0):
        """Remove a private stage, retrying delayed Windows file releases."""
        if not path:
            return
        path = Path(path)
        try:
            shutil.rmtree(str(path))
        except FileNotFoundError:
            return
        except OSError:
            if attempt < 8:
                QTimer.singleShot(
                    250,
                    lambda path=path, attempt=attempt + 1:
                    self._remove_stage(path, attempt),
                )

    def _finish(self):
        self.package_layers.clear()
        stages = [entry['stage'] for entry in self.pending_vectors]
        for entry in self.pending_vectors:
            entry['path'] = None
        self.pending_vectors.clear()
        if self.package_stage:
            stages.append(self.package_stage)
            self.package_stage = None
        self.package_file = None
        self.staged_file = None
        self._retired_tasks.clear()
        for stage in stages:
            self._remove_stage(stage)
        if self.set_project_crs and any(r['status'] == 'success' for r in self.results):
            self.project.setCrs(self.target)
        self.active = False
        self.progressChanged.emit(100)
        self.finished.emit(self.results, '')
