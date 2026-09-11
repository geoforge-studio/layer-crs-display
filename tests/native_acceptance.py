"""Run inside QGIS Python Console; creates and converts only temporary fixtures.
exec(open('/path/to/layer_crs_display/tests/native_acceptance.py', encoding='utf-8').read())
Requires the installed plugin, Processing and GDAL. Not run in the build environment.
"""
import hashlib
import tempfile
from pathlib import Path
from qgis.PyQt.QtCore import QEventLoop, QTimer, QVariant
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsField, QgsFeature, QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem)
from osgeo import gdal
from layer_crs_display.batch_engine import BatchRunner, eligibility
from layer_crs_display.batch_logic import plan_outputs

assert QgsApplication.processingRegistry().algorithmById('native:reprojectlayer')
assert QgsApplication.processingRegistry().algorithmById('gdal:warpreproject')
with tempfile.TemporaryDirectory(prefix='crs_native_test_') as folder:
    folder=Path(folder)
    # Use an independent project so the user's layers are untouched.
    project=QgsProject()
    vector=QgsVectorLayer('Point?crs=EPSG:4326','نقطه آزمون','memory')
    vector.dataProvider().addAttributes([QgsField('label',QVariant.String)])
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
    layers=[vector,raster]
    target=QgsCoordinateReferenceSystem('EPSG:32639')
    plans=plan_outputs([dict(layer_id=l.id(),name=l.name(),kind='vector' if l is vector else 'raster',source_wkt=l.crs().toWkt()) for l in layers],folder,'_39')
    runner=BatchRunner(project);loop=QEventLoop();completed=[]
    runner.finished.connect(lambda rows,report:(completed.extend(rows),loop.quit()))
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(lambda:(runner.cancel(),loop.quit()))
    timer.start(60000);runner.start(plans,target,add_layers=False);loop.exec_();timer.stop()
    # Do not free context while a timed-out task is still running.
    if runner.active:
        runner.finished.connect(lambda *args:loop.quit());loop.exec_()
        raise AssertionError('Native test timed out')
    assert [r['status'] for r in completed]==['success','success'],completed
    output=QgsVectorLayer(plans[0]['output_path'],'test output','ogr')
    assert output.isValid() and output.crs()==target and output.featureCount()==1
    feature=next(output.getFeatures());point=feature.geometry().asPoint()
    assert abs(point.x()-500000)<.05 and abs(point.y())<.05,point
    assert feature['label']=='آزمون فارسی'
    assert vector.crs().authid()=='EPSG:4326'
    assert next(vector.getFeatures()).geometry().asPoint().x()==51
    ds=gdal.Open(plans[1]['output_path']);assert ds
    assert ds.GetGeoTransform()[0]>400000
    assert set(ds.GetRasterBand(1).ReadRaster()) <= {1,2,255}
    assert ds.GetRasterBand(1).GetNoDataValue()==255
    assert QgsCoordinateReferenceSystem(ds.GetProjection())==target
    assert hashlib.sha256(src.read_bytes()).hexdigest()==before
    assert eligibility(output,target)
    output=None;ds=None;project.clear();raster=None;vector=None
print('Native acceptance passed: real vector/raster reprojection, attributes, categorical values, NoData and source preservation.')
