"""Real Qt, real filesystem; explicit fake GIS/provider/task boundaries.
This does NOT validate coordinate transformation, GDAL or native QGIS.
Run with PyQt5 installed and QT_QPA_PLATFORM=offscreen.
"""
import json
import sys
import tempfile
import types
from pathlib import Path
from PyQt5 import QtCore, QtWidgets, QtGui

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
qgis=types.ModuleType('qgis'); core=types.ModuleType('qgis.core'); gui=types.ModuleType('qgis.gui')
sys.modules.update({'qgis':qgis,'qgis.core':core,'qgis.gui':gui,'qgis.PyQt':types.ModuleType('qgis.PyQt'),
    'qgis.PyQt.QtCore':QtCore,'qgis.PyQt.QtWidgets':QtWidgets,'qgis.PyQt.QtGui':QtGui})


class CRS:
    def __init__(self,value=''):self.value=value.value if isinstance(value,CRS) else value
    def isValid(self):return bool(self.value)
    def authid(self):return self.value
    def description(self):return self.value
    def toWkt(self):return self.value
    def __eq__(self,other):return isinstance(other,CRS) and self.value==other.value


class Vector:
    def __init__(self,path,name,provider='ogr'):
        self.path,self.title,self.provider=path,name,provider
        self.data=json.loads(Path(path).read_text()) if Path(path).is_file() else {}
    def id(self):return self.path
    def name(self):return self.title
    def setName(self,name):self.title=name
    def isValid(self):return bool(self.data)
    def isSpatial(self):return True
    def isEditable(self):return bool(self.data.get('editable'))
    def crs(self):return CRS(self.data.get('crs',''))
    def featureCount(self):return self.data.get('count',0)
    def subsetString(self):return 'county = 1'
    def providerType(self):return self.provider


class Raster:
    pass

for name,value in Vector.__dict__.items():
    if callable(value):setattr(Raster,name,value)


class Node:
    def __init__(self,layer):self.value=layer;self.visible=True
    def layer(self):return self.value
    def layerId(self):return self.value.id()
    def setItemVisibilityChecked(self,value):self.visible=value


class Project:
    current=None
    def __init__(self,layers):self.layers={x.id():x for x in layers};self.nodes={x.id():Node(x) for x in layers};self.projection=CRS('EPSG:32639')
    @classmethod
    def instance(cls):return cls.current
    def crs(self):return self.projection
    def setCrs(self,crs):self.projection=crs
    def mapLayer(self,key):return self.layers.get(key)
    def layerTreeRoot(self):return self
    def findLayers(self):return list(self.nodes.values())
    def findLayer(self,key):return self.nodes.get(key)
    def addMapLayer(self,layer):self.layers[layer.id()]=layer;self.nodes[layer.id()]=Node(layer)
    def transformContext(self):return None


class Settings:
    data={}
    def value(self,key,default=None,**kw):return self.data.get(key,default)
    def setValue(self,key,value):self.data[key]=value


class ProjectionWidget(QtWidgets.QWidget):
    crsChanged=QtCore.pyqtSignal()
    def __init__(self):super().__init__();self.value=CRS()
    def setCrs(self,value):self.value=value;self.crsChanged.emit()
    def crs(self):return self.value


class Feedback(QtCore.QObject):
    progressChanged=QtCore.pyqtSignal(float)
    def __init__(self):super().__init__();self.cancelled=False
    def cancel(self):self.cancelled=True
    def textLog(self):return 'Fake provider failure'
    def reportError(self,*args):pass


class Context:
    def setProject(self,x):pass
    def setTransformContext(self,x):pass
    def setInvalidGeometryCheck(self,x):pass


class Style:
    def readFromLayer(self,x):pass
    def writeToLayer(self,x):pass


class Task(QtCore.QObject):
    executed=QtCore.pyqtSignal(bool,object)
    calls=[]
    def __init__(self,algorithm,params,context,feedback):
        super().__init__();self.params=params;self.feedback=feedback;self.cancelled=False;self.algorithm=algorithm
    def setDependentLayers(self,x):pass
    def cancel(self):self.cancelled=True
    def isCanceled(self):return self.cancelled
    def execute(self):
        Task.calls.append((self.algorithm,self.params.copy()))
        data=self.params['INPUT'].data.copy()
        data['crs']=self.params['TARGET_CRS'].authid()
        if data.get('bad_crs'):data['crs']='EPSG:4326'
        if data.get('bad_count'):data['count']-=1
        Path(self.params['OUTPUT']).write_text(json.dumps(data))
        if data.get('report_error'):self.feedback.reportError('Transformation failed for a feature')
        self.executed.emit(not data.get('fail',False),{'OUTPUT':self.params['OUTPUT']})


manager=types.SimpleNamespace(addTask=lambda task:QtCore.QTimer.singleShot(0,task.execute))
registry=types.SimpleNamespace(algorithmById=lambda key:key)
for name,value in dict(QgsCoordinateReferenceSystem=CRS,QgsVectorLayer=Vector,QgsRasterLayer=Raster,
    QgsProject=Project,QgsSettings=Settings,QgsProcessingFeedback=Feedback,QgsProcessingContext=Context,
    QgsMapLayerStyle=Style,QgsFeatureRequest=types.SimpleNamespace(GeometryAbortOnInvalid=2),
    QgsProcessingAlgRunnerTask=Task,QgsApplication=types.SimpleNamespace(processingRegistry=lambda:registry,taskManager=lambda:manager)).items():setattr(core,name,value)
gui.QgsProjectionSelectionWidget=ProjectionWidget

from layer_crs_display.batch_engine import BatchRunner, eligibility
from layer_crs_display.batch_dialog import BatchDialog
from layer_crs_display.batch_logic import plan_outputs
app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

# Exercise actual plugin methods for upgrade compatibility, with fake registry
# types only. Existing unrelated layer-widget entries must survive migration.
core.Qgis = types.SimpleNamespace(Info=0)
core.QgsLayerTreeModel = types.SimpleNamespace(UseEmbeddedWidgets=1)
gui.QgsGui = types.SimpleNamespace()
gui.QgsLayerTreeEmbeddedWidgetProvider = object
from layer_crs_display.plugin import LayerCrsDisplayPlugin
from layer_crs_display.crs_widget import PROVIDER_ID


class WidgetLayer:
    def __init__(self):
        self.properties = {
            'embeddedWidgets/count': 3,
            'embeddedWidgets/0/id': 'other_widget',
            'embeddedWidgets/1/id': 'legacy_layer_crs_display',
            'embeddedWidgets/2/id': PROVIDER_ID,
        }
    def customProperty(self, key, default=None):
        return self.properties.get(key, default)
    def setCustomProperty(self, key, value):
        self.properties[key] = value
    def removeCustomProperty(self, key):
        self.properties.pop(key, None)


controller = LayerCrsDisplayPlugin.__new__(LayerCrsDisplayPlugin)
widget_layer = WidgetLayer()
controller._add_widget_to_layer(widget_layer)
assert controller._embedded_widget_ids(widget_layer) == ['other_widget', PROVIDER_ID]
controller._add_widget_to_layer(widget_layer)
assert controller._embedded_widget_ids(widget_layer) == ['other_widget', PROVIDER_ID]
controller._remove_widget_from_layer(widget_layer)
assert controller._embedded_widget_ids(widget_layer) == ['other_widget']


def source(folder,name,crs='EPSG:4326',**extra):
    path=Path(folder)/(name+'.json')
    path.write_text(json.dumps(dict(crs=crs,count=3,**extra)))
    return Vector(str(path),name)


def plans(layers,folder):
    return plan_outputs([dict(layer_id=l.id(),name=l.name(),kind='vector',source_wkt=l.crs().toWkt()) for l in layers],folder,'_39')


def wait(runner):
    for _ in range(100):
        app.processEvents()
        if not runner.active:return
    raise AssertionError('Runner did not finish')


with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/'out').mkdir()
    a=source(root,'roads'); same=source(root,'same','EPSG:32639');unknown=source(root,'unknown','')
    Project.current=Project([a,same,unknown])
    iface=types.SimpleNamespace(layerTreeView=lambda:types.SimpleNamespace(selectedLayers=lambda:[a]))
    for width,height in [(360,240),(640,360),(1024,600)]:
        dialog=BatchDialog(iface)
        dialog.resize(width,height);dialog.folder.setText(str(root/'out'));dialog.suffix.setText('_39')
        dialog.show();app.processEvents()
        assert dialog.table.rowCount()==3
        assert dialog.table.item(0,0).checkState()==QtCore.Qt.Checked
        assert not dialog.table.item(1,0).data(QtCore.Qt.UserRole)
        assert not dialog.table.item(2,0).data(QtCore.Qt.UserRole)
        assert dialog.run_button.isEnabled()
        for button in (dialog.run_button,dialog.cancel_button,dialog.close_button):
            point=button.mapTo(dialog,QtCore.QPoint(0,0))
            assert dialog.rect().contains(QtCore.QRect(point,button.size()))
        dialog.search.setText('unknown');app.processEvents()
        assert dialog.table.isRowHidden(0) and not dialog.table.isRowHidden(2)
        assert '1 selected hidden' in dialog.summary.text()
        assert len(dialog.selected_items())==1
        dialog.search.clear()
        dialog.advanced_button.setChecked(True);app.processEvents()
        assert dialog.options.isVisible()
        dialog.advanced_button.setChecked(False)
        dialog.scroll.verticalScrollBar().setValue(0);app.processEvents()
        assert dialog.run_button.isVisible()
        assert dialog.width()<=width and dialog.height()<=height
        dialog.select('none');assert not dialog.run_button.isEnabled()
        dialog.select('selected');assert dialog.run_button.isEnabled()
        dialog.close()

    # Successful publication and source preservation; both operate on fake data.
    project=Project([a]);runner=BatchRunner(project)
    runner.start(plans([a],root/'out'),CRS('EPSG:32639'),hide_sources=True,project_crs=True)
    wait(runner)
    assert runner.results[0]['status']=='success'
    assert (root/'out/roads_39.gpkg').exists()
    assert a.crs()==CRS('EPSG:4326') and a.name()=='roads'
    assert not project.nodes[a.id()].visible
    assert len(project.layers)==2
    assert Task.calls[-1][0]=='native:reprojectlayer'
    saved=(root/'out/roads_39.gpkg').read_bytes()
    # Late file collision after planning must not overwrite.
    stale=plans([a],root/'out');stale[0]['error']=''
    runner.start(stale,CRS('EPSG:32639'));wait(runner)
    assert runner.results[0]['status']=='failed'
    assert (root/'out/roads_39.gpkg').read_bytes()==saved

    # Failure in one row doesn't prevent the next; no partial final publication.
    for fault in ['fail','bad_crs','bad_count','report_error']:
        out=root/fault;out.mkdir();bad=source(root,fault,**{fault:True});good=source(root,'good_'+fault)
        runner=BatchRunner(Project([bad,good]));runner.start(plans([bad,good],out),CRS('EPSG:32639'));wait(runner)
        assert [r['status'] for r in runner.results]==['failed','success'],runner.results
        assert not (out/(fault+'_39.gpkg')).exists()
        assert not list(out.glob('crs_stage_*'))

    # Immediate cancel and mid-task cancel do not publish final files.
    for midway in (False,True):
        out=root/('cancel'+str(midway));out.mkdir();runner=BatchRunner(Project([a]))
        if midway:runner.rowChanged.connect(lambda key,status,text:runner.cancel() if status=='running' else None)
        runner.start(plans([a],out),CRS('EPSG:32639'))
        if not midway:runner.cancel()
        wait(runner);assert runner.results[0]['status']=='cancelled'
        assert not (out/'roads_39.gpkg').exists()

    # Raster parameters reach the GDAL warp task (still a fake provider).
    out=root/'raster';out.mkdir()
    raster=Raster(a.path,'image','gdal')
    runner=BatchRunner(Project([raster]))
    jobs=plan_outputs([dict(layer_id=raster.id(),name='image',kind='raster',source_wkt=raster.crs().toWkt())],out,'_39')
    runner.start(jobs,CRS('EPSG:32639'),resampling=1,add_layers=False);wait(runner)
    assert runner.results[0]['status']=='success'
    algorithm,params=Task.calls[-1]
    assert algorithm=='gdal:warpreproject'
    assert params['RESAMPLING']==1 and params['MULTITHREADING'] is True
    assert params['SOURCE_CRS']==CRS('EPSG:4326') and params['DATA_TYPE']==0
    assert (out/'image_39.tif').exists()

print('PASS: widget migration retains unrelated IDs; real Qt at 3 viewport sizes; fake GIS tasks verify success, failure continuation, CRS/count checks, reported transform error, cancellation and collision protection. No native reprojection tested.')
