"""Real Qt, real filesystem; explicit fake GIS/provider/task boundaries.
This does NOT validate coordinate transformation, GDAL or native QGIS.
Run with PyQt6 or PyQt5 installed and QT_QPA_PLATFORM=offscreen.
"""
import json
import sys
import tempfile
import types
from pathlib import Path
try:
    from PyQt6 import QtCore, QtWidgets, QtGui
except ImportError:
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
        filename, _, table = path.partition('|layername=')
        self.data=json.loads(Path(filename).read_text()) if Path(filename).is_file() else {}
        if table:self.data=self.data.get('layers',{}).get(table,{})
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
    package_fault=''
    def __init__(self,algorithm,params,context,feedback):
        super().__init__();self.params=params;self.feedback=feedback;self.cancelled=False;self.algorithm=algorithm
    def setDependentLayers(self,x):pass
    def cancel(self):self.cancelled=True
    def isCanceled(self):return self.cancelled
    def execute(self):
        Task.calls.append((self.algorithm,self.params.copy()))
        if self.algorithm == 'native:package':
            data = {'layers': {layer.name(): layer.data for layer in self.params['LAYERS']}}
            if Task.package_fault == 'missing_layer':
                data['layers'].pop(next(iter(data['layers'])))
            Path(self.params['OUTPUT']).write_text(json.dumps(data))
            self.executed.emit(Task.package_fault != 'fail', {'OUTPUT': self.params['OUTPUT']})
            return
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
    QgsProcessingAlgRunnerTask=Task,QgsApplication=types.SimpleNamespace(processingRegistry=lambda:registry,taskManager=lambda:manager),
    Qgis=types.SimpleNamespace(
        InvalidGeometryCheck=types.SimpleNamespace(AbortOnInvalid=2),
        MessageLevel=types.SimpleNamespace(Info=0)),
    QgsLayerTreeModel=types.SimpleNamespace(
        Flag=types.SimpleNamespace(UseEmbeddedWidgets=1))).items():setattr(core,name,value)
gui.QgsProjectionSelectionWidget=ProjectionWidget

from layer_crs_display.batch_engine import BatchRunner, eligibility, same_crs
from layer_crs_display.batch_dialog import BatchDialog
from layer_crs_display.batch_logic import plan_outputs
from layer_crs_display.about_dialog import AboutDialog, PLUGIN_LINKS, SOCIAL_LINKS
app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

opened_urls = []
about = AboutDialog(
    '0.8.2',
    url_opener=lambda url: opened_urls.append(url.toString()),
)
about.show()
app.processEvents()
for _caption, expected_url, object_name in PLUGIN_LINKS:
    button = about.findChild(QtWidgets.QPushButton, object_name)
    assert button is not None
    button.click()
    assert opened_urls[-1] == expected_url
for _caption, expected_url, object_name, _icon_name in SOCIAL_LINKS:
    button = about.findChild(QtWidgets.QPushButton, object_name)
    assert button is not None and not button.icon().isNull()
    button.click()
    assert opened_urls[-1] == expected_url
email_button = about.findChild(QtWidgets.QPushButton, 'emailLink')
assert email_button is not None
email_button.click()
assert opened_urls[-1] == 'mailto:reynolds.mach88@gmail.com'
assert about.findChild(QtWidgets.QLabel, 'aboutVersion').text() == 'Version 0.8.2  |  QGIS 3 / 4'
about.close()

assert same_crs(CRS('EPSG:32639'), CRS('EPSG:32639'))
assert not same_crs(CRS('EPSG:32639'), CRS('EPSG:32739'))
assert not same_crs(CRS(), CRS())
epoch_a, epoch_b = CRS('EPSG:32639'), CRS('EPSG:32639')
epoch_a.coordinateEpoch = lambda: 2020.0
epoch_b.coordinateEpoch = lambda: 2021.0
assert not same_crs(epoch_a, epoch_b)

# Exercise actual plugin methods for upgrade compatibility, with fake registry
# types only. Existing unrelated layer-widget entries must survive migration.
gui.QgsGui = types.SimpleNamespace()
gui.QgsLayerTreeEmbeddedWidgetProvider = object
from layer_crs_display.plugin import LayerCrsDisplayPlugin
from layer_crs_display.crs_widget import PROVIDER_ID


class ToolbarIface:
    def __init__(self):
        self.window = QtWidgets.QMainWindow()
        self.menu_actions = []

    def mainWindow(self):
        return self.window

    def addToolBar(self, title):
        toolbar = QtWidgets.QToolBar(title, self.window)
        self.window.addToolBar(toolbar)
        return toolbar

    def addPluginToMenu(self, _menu, action):
        self.menu_actions.append(action)

    def removePluginMenu(self, _menu, action):
        if action in self.menu_actions:
            self.menu_actions.remove(action)


toolbar_iface = ToolbarIface()
toolbar_controller = LayerCrsDisplayPlugin.__new__(LayerCrsDisplayPlugin)
toolbar_controller.iface = toolbar_iface
toolbar_controller.toolbar = None
toolbar_controller.toggle_action = None
toolbar_controller.batch_action = None
toolbar_controller.settings_action = None
toolbar_controller.about_action = None
toolbar_controller.read_settings = lambda: {
    'enabled': False,
    'display_format': 'authid',
}
toolbar_controller._create_actions()
assert toolbar_controller.toolbar.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
assert toolbar_controller.toolbar.iconSize() == QtCore.QSize(28, 28)
display_button = toolbar_controller.toolbar.widgetForAction(
    toolbar_controller.toggle_action
)
reproject_button = toolbar_controller.toolbar.widgetForAction(
    toolbar_controller.batch_action
)
assert display_button.objectName() == 'GeoForgeDisplayCrsButton'
assert reproject_button.objectName() == 'GeoForgeReprojectButton'
assert 'border: 1px solid palette(mid)' in toolbar_controller.toolbar.styleSheet()
assert display_button.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
assert reproject_button.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
toolbar_controller.toolbar.setToolButtonStyle(
    QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
)
app.processEvents()
assert toolbar_controller.toolbar.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
assert display_button.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
assert reproject_button.toolButtonStyle() == (
    QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
)
off_icon_key = toolbar_controller.toggle_action.icon().cacheKey()
toolbar_controller._update_display_icon(True)
assert toolbar_controller.toggle_action.icon().cacheKey() != off_icon_key
toolbar_controller._remove_actions()


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
        assert dialog.table.item(0,0).checkState()==QtCore.Qt.CheckState.Checked
        assert not dialog.table.item(1,0).data(QtCore.Qt.ItemDataRole.UserRole)
        assert not dialog.table.item(2,0).data(QtCore.Qt.ItemDataRole.UserRole)
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
    assert (root/'out/reprojected.gpkg').exists()
    assert set((root/'out').iterdir()) == {root/'out/reprojected.gpkg'}
    assert a.crs()==CRS('EPSG:4326') and a.name()=='roads'
    assert not project.nodes[a.id()].visible
    assert len(project.layers)==2
    assert Task.calls[-1][0]=='native:package'
    assert not Task.calls[-1][1]['EXPORT_RELATED_LAYERS']
    saved=(root/'out/reprojected.gpkg').read_bytes()
    # Late file collision after planning must not overwrite.
    stale=plans([a],root/'out');stale[0]['error']=''
    runner.start(stale,CRS('EPSG:32639'));wait(runner)
    assert runner.results[0]['status']=='failed'
    assert (root/'out/reprojected.gpkg').read_bytes()==saved

    # Multiple converted layers share exactly one file; same-CRS input is skipped
    # even if a stale or external caller explicitly includes it in the plans.
    out=root/'shared';out.mkdir();b=source(root,'rivers')
    runner=BatchRunner(Project([a,b,same]));before_calls=len(Task.calls)
    runner.start(plans([a,same,b],out),CRS('EPSG:32639'));wait(runner)
    assert [r['status'] for r in runner.results]==['success','skipped','success'],runner.results
    assert list(out.glob('*.gpkg'))==[out/'reprojected.gpkg']
    assert set(json.loads((out/'reprojected.gpkg').read_text())['layers'])=={'roads_39','rivers_39'}
    assert len([c for c in Task.calls[before_calls:] if c[0]=='native:reprojectlayer'])==2
    assert runner.results[0]['output_uri'].endswith('|layername=roads_39')
    assert len(runner.project.layers)==5
    assert set(out.iterdir()) == {out/'reprojected.gpkg'}

    out=root/'all_same';out.mkdir();runner=BatchRunner(Project([same]));before_calls=len(Task.calls)
    runner.start(plans([same],out),CRS('EPSG:32639'));wait(runner)
    assert runner.results[0]['status']=='skipped'
    assert len(Task.calls)==before_calls and not list(out.glob('*.gpkg'))

    # Failure in one row doesn't prevent the next; no partial final publication.
    for fault in ['fail','bad_crs','bad_count','report_error']:
        out=root/fault;out.mkdir();bad=source(root,fault,**{fault:True});good=source(root,'good_'+fault)
        runner=BatchRunner(Project([bad,good]));runner.start(plans([bad,good],out),CRS('EPSG:32639'));wait(runner)
        assert [r['status'] for r in runner.results]==['failed','success'],runner.results
        assert not (out/(fault+'_39.gpkg')).exists()
        assert set(json.loads((out/'reprojected.gpkg').read_text())['layers'])=={'good_'+fault+'_39'}
        assert set(out.iterdir()) == {out/'reprojected.gpkg'}

    # Immediate cancel and mid-task cancel do not publish final files.
    for midway in (False,True):
        out=root/('cancel'+str(midway));out.mkdir();runner=BatchRunner(Project([a]))
        if midway:runner.rowChanged.connect(lambda key,status,text:runner.cancel() if status=='running' else None)
        runner.start(plans([a],out),CRS('EPSG:32639'))
        if not midway:runner.cancel()
        wait(runner);assert runner.results[0]['status']=='cancelled'
        assert not (out/'reprojected.gpkg').exists()

    # Package failure, incomplete packaging and packaging cancellation must not
    # expose a partial final container or hide sources.
    for fault in ('fail','missing_layer','cancel'):
        out=root/('package_'+fault);out.mkdir();runner=BatchRunner(Project([a,b]))
        Task.package_fault=fault
        if fault=='cancel':
            runner.rowChanged.connect(lambda key,status,text:runner.cancel() if status=='packaging' else None)
        runner.start(plans([a,b],out),CRS('EPSG:32639'),hide_sources=True);wait(runner)
        assert all(r['status']==('cancelled' if fault=='cancel' else 'failed') for r in runner.results)
        assert not list(out.glob('*.gpkg')) and not list(out.glob('crs_stage_*'))
        assert all(node.visible for node in runner.project.nodes.values())
    Task.package_fault=''

    out=root/'cancel_staged';out.mkdir();runner=BatchRunner(Project([a,b]))
    runner.rowChanged.connect(lambda key,status,text:runner.cancel() if status=='staged' else None)
    runner.start(plans([a,b],out),CRS('EPSG:32639'));wait(runner)
    assert all(r['status']=='cancelled' for r in runner.results)
    assert not list(out.glob('*.gpkg')) and not list(out.glob('crs_stage_*'))

    # A competing file created during packaging must be left untouched.
    out=root/'package_collision';out.mkdir();runner=BatchRunner(Project([a]))
    runner.rowChanged.connect(lambda key,status,text:(out/'reprojected.gpkg').write_bytes(b'keep') if status=='packaging' else None)
    runner.start(plans([a],out),CRS('EPSG:32639'));wait(runner)
    assert runner.results[0]['status']=='failed' and (out/'reprojected.gpkg').read_bytes()==b'keep'

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

print('PASS: real Qt at 3 sizes; widget migration; simulated GIS verifies one shared GeoPackage, same-CRS exclusion, distinct layer URIs, CRS/count checks, failure continuation, packaging failures/cancellation, late collisions and raster parameters. No native reprojection tested.')
