"""Run inside QGIS Python Console; creates and converts only temporary fixtures.
exec(open('/path/to/layer_crs_display/tests/native_acceptance.py', encoding='utf-8').read())
Requires the installed plugin, Processing and GDAL. Not run in the build environment.
"""
import hashlib
import sqlite3
import tempfile
from pathlib import Path
from qgis.PyQt.QtCore import QEventLoop, QMetaType, QTimer
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem)
from osgeo import gdal, osr
from layer_crs_display.batch_engine import BatchRunner, eligibility, same_crs
from layer_crs_display.batch_logic import plan_outputs

assert QgsApplication.processingRegistry().algorithmById('native:reprojectlayer')
assert QgsApplication.processingRegistry().algorithmById('gdal:warpreproject')
assert QgsApplication.processingRegistry().algorithmById('native:package')
with tempfile.TemporaryDirectory(prefix='crs_native_test_') as folder:
    folder=Path(folder)
    # Use an independent project so the user's layers are untouched.
    project=QgsProject()
    vector=QgsVectorLayer('Point?crs=EPSG:4326','نقطه آزمون','memory')
    vector.dataProvider().addAttributes(
        [QgsField('label', QMetaType.Type.QString)]
    )
    vector.updateFields()
    f=QgsFeature(vector.fields());f.setAttributes(['آزمون فارسی'])
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(51,0)))
    assert vector.dataProvider().addFeatures([f])[0]
    vector.updateExtents();project.addMapLayer(vector)
    src=folder/'classes.tif'
    ds=gdal.GetDriverByName('GTiff').Create(str(src),4,4,1,gdal.GDT_Byte)
    ds.SetGeoTransform((50.99,.005,0,.02,0,-.005))
    ds.SetProjection(QgsCoordinateReferenceSystem('EPSG:4326').toWkt())
    band=ds.GetRasterBand(1);band.SetNoDataValue(255)
    band.WriteRaster(0,0,4,4,bytes([1,1,2,2,1,1,2,2,1,1,2,2,255,255,2,2]))
    band=None;ds=None
    before=hashlib.sha256(src.read_bytes()).hexdigest()
    raster=QgsRasterLayer(str(src),'classes','gdal');assert raster.isValid();project.addMapLayer(raster)
    target=QgsCoordinateReferenceSystem('EPSG:32639')
    second=QgsVectorLayer('Point?crs=EPSG:4326','second','memory')
    second.dataProvider().addAttributes(
        [QgsField('label', QMetaType.Type.QString)]
    )
    second.updateFields()
    f2=QgsFeature(second.fields());f2.setAttributes(['second point'])
    f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(51.001,0)))
    assert second.dataProvider().addFeatures([f2])[0]
    second.updateExtents();project.addMapLayer(second)
    already=QgsVectorLayer('Point?crs=EPSG:32639','already_target','memory')
    project.addMapLayer(already)
    equivalent=osr.SpatialReference();equivalent.ImportFromEPSG(32639);equivalent.MorphToESRI()
    assert same_crs(QgsCoordinateReferenceSystem(equivalent.ExportToWkt()),target)
    assert not same_crs(QgsCoordinateReferenceSystem('EPSG:32638'),target)
    assert not same_crs(QgsCoordinateReferenceSystem('EPSG:32739'),target)
    layers=[vector,raster,already,second]
    plans=plan_outputs([dict(layer_id=l.id(),name=l.name(),kind='vector' if isinstance(l,QgsVectorLayer) else 'raster',source_wkt=l.crs().toWkt()) for l in layers],folder,'_39')
    runner=BatchRunner(project);loop=QEventLoop();completed=[]
    runner.finished.connect(lambda rows,report:(completed.extend(rows),loop.quit()))
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(lambda:(runner.cancel(),loop.quit()))
    timer.start(60000);runner.start(plans,target,add_layers=False);loop.exec();timer.stop()
    # Do not free context while a timed-out task is still running.
    if runner.active:
        runner.finished.connect(lambda *args:loop.quit());loop.exec()
        raise AssertionError('Native test timed out')
    assert [r['status'] for r in completed]==['success','success','skipped','success'],completed
    assert list(folder.glob('*.gpkg')) == [folder/'reprojected.gpkg']
    with sqlite3.connect(str(folder/'reprojected.gpkg')) as conn:
        tables={r[0] for r in conn.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")}
    conn.close()
    assert tables == {plans[0]['output_layer'],plans[3]['output_layer']},tables
    output=QgsVectorLayer(completed[0]['output_uri'],'test output','ogr')
    assert output.isValid() and output.crs()==target and output.featureCount()==1
    feature=next(output.getFeatures());point=feature.geometry().asPoint()
    assert abs(point.x()-500000)<.05 and abs(point.y())<.05,point
    assert feature['label']=='آزمون فارسی'
    output2=QgsVectorLayer(completed[3]['output_uri'],'second output','ogr')
    assert output2.isValid() and output2.crs()==target and output2.featureCount()==1
    assert next(output2.getFeatures())['label']=='second point'
    assert vector.crs().authid()=='EPSG:4326'
    assert next(vector.getFeatures()).geometry().asPoint().x()==51
    ds=gdal.Open(plans[1]['output_path']);assert ds
    assert ds.GetGeoTransform()[0]>400000
    assert set(ds.GetRasterBand(1).ReadRaster()) <= {1,2,255}
    assert ds.GetRasterBand(1).GetNoDataValue()==255
    assert QgsCoordinateReferenceSystem(ds.GetProjection())==target
    assert hashlib.sha256(src.read_bytes()).hexdigest()==before
    assert eligibility(output,target)
    output=None;output2=None;ds=None;project.clear();raster=None;vector=None;second=None;already=None;layers=[]
print('Native acceptance passed: one GeoPackage with two converted vector layers, same-CRS exclusion, CRS aliases, real vector/raster reprojection, attributes, categorical values, NoData and source preservation.')
