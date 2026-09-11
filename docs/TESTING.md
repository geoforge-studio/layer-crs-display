# Testing Layer CRS Display

## Automated checks without QGIS

From the repository root, run:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen python tests/qt_batch_acceptance.py
python tools/build_zip.py
```

The second command needs PyQt5 in the test environment. On Windows PowerShell,
set `$env:QT_QPA_PLATFORM = 'offscreen'` and run the Python command separately.
These tests use simulated GIS objects; they are not native reprojection tests.

## Native acceptance (required before claiming support)

1. Use a QGIS 3 installation and a disposable project/profile. Enable Processing
   and its GDAL provider. QGIS 4/Qt6 is not supported by this candidate.
2. Disable any older installed version, install the generated ZIP through
   **Plugins > Manage and Install Plugins > Install from ZIP**, then restart QGIS.
3. Confirm the **CRS** toolbar has **Display CRS** and **Reproject** buttons.
   Toggle the display, change settings, unload/reload, and open an older project
   to check that it has one CRS widget per layer and unrelated widgets are kept.
4. Download the source repository for the installed version and extract it.
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

5. Run a batch containing two vector layers needing conversion and one already in the target CRS. Confirm that exactly one GeoPackage contains only the two converted layers and that both load using their own layer names. Repeat with a custom GeoPackage filename and with raster inputs (GeoTIFF). Run small real vector and raster batches through the dialog. Test an existing
   output conflict, cancellation, filtered input, custom suffix, missing source
   CRS and a transformation requiring a locally installed datum grid.
6. Record QGIS, Qt, GDAL and OS versions, results and any traceback. Do not mark
   untested platforms or versions as passed. Add authentic screenshots only after
   the interface has been exercised in native QGIS.

## Installation archive security scan

Scan the **extracted installation ZIP** with Bandit before submission. Use its
default rules without suppressions. Development tests remain available under
`tests/` in the public repository; no test code is imported by the plugin.

## Current status

The maintainer reported a successful basic QGIS check of 0.5.2. The complete native acceptance suite and an exact QGIS/OS version record are still pending. The declared 3.22–3.x metadata range is
inherited from the supplied version and is not a tested-platform matrix.
