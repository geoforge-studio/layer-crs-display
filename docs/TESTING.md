# Testing Layer CRS Display

## Automated checks without QGIS

From the repository root, run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen python tests/qt_batch_acceptance.py
python tools/build_zip.py
```

The second command uses PyQt6 when available and otherwise PyQt5. On Windows PowerShell,
set `$env:QT_QPA_PLATFORM = 'offscreen'` and run the Python command separately.
These tests use simulated GIS objects; they are not native reprojection tests.

## Native acceptance (required before claiming support)

1. Prepare one supported QGIS 3/Qt5 installation and one QGIS 4/Qt6 installation,
   each with a disposable project/profile. Enable Processing and its GDAL provider.
2. Disable any older installed version, install the generated ZIP through
   **Plugins > Manage and Install Plugins > Install from ZIP**, then restart QGIS.
3. Confirm the **CRS** toolbar has **Display CRS**, **CRS Audit** and
   **Reproject** buttons in that order.
   Toggle the display, change settings, unload/reload, and open an older project
   to check that it has one CRS widget per layer and unrelated widgets are kept.
4. Open **CRS Audit** in a mixed vector/raster project. Change the Reference CRS
   and verify `OK`, `Different` and `Missing` classifications, the summary and
   every filter update against that reference. Confirm Refresh does not change
   any layer or project CRS. Select `Different` rows, send them to Reproject,
   and confirm only eligible selected layers are checked with the same reference
   CRS as target. Confirm Missing layers are never transferred.

5. Download the source repository for the installed version and extract it.
   Development tests are kept in the repository and are not installed with the
   plugin. Open the QGIS Python Console and run the following, replacing the
   example path with the extracted repository directory:

```python
from pathlib import Path
repository = Path(r'C:/path/to/layer-crs-display')
script = repository / 'tests' / 'native_acceptance.py'
exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'))
```

The script creates temporary input data in an independent project, converts a
point from EPSG:4326 to EPSG:32639 (expected 500000, 0 at longitude 51, latitude 0),
checks two named vector layers in one GeoPackage, excludes an already matching CRS, checks a categorical raster and NoData, and verifies unchanged input data.
Do not close QGIS while it is running. If a provider hangs, cancellation may take
time; the test waits for the task to finish before freeing its context.

6. Run a batch containing two vector layers needing conversion and one already in the target CRS. In an initially empty output folder, confirm that exactly one file—the GeoPackage—contains only the two converted layers, that both load using their own layer names, and that no `crs_stage_*` folder or JSON report is created. Repeat with a custom GeoPackage filename and with raster inputs (GeoTIFF). Run small real vector and raster batches through the dialog. Test an existing
   output conflict, cancellation, filtered input, custom suffix, missing source
   CRS and a transformation requiring a locally installed datum grid.
7. Repeat the complete test independently in QGIS 3 and QGIS 4. Record QGIS, Qt,
   Python, GDAL and OS versions, results and any traceback for each run. Do not
   mark untested platforms or versions as passed. Add authentic screenshots only
   after the interface has been exercised in native QGIS.

## Installation archive security scan

Scan the **extracted installation ZIP** with Bandit before submission. Use its
default rules without suppressions. Development tests remain available under
`tests/` in the public repository; no test code is imported by the plugin.

## Current status

The maintainer reported successful functional checks of the 0.7.0 candidate in
both QGIS 3 and QGIS 4 and a successful functional smoke test of 0.8.2. Version
0.8.2 is marked stable by maintainer decision. Exact QGIS, Qt, Python, GDAL and
OS versions and the complete native acceptance output have not yet been
recorded. The declared 3.22–4.x metadata range is a compatibility range, not a
claim that every release and platform combination was tested.
