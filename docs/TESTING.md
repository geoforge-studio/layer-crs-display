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
4. Open the QGIS Python Console and run the following using the installed plugin:

```python
from pathlib import Path
import layer_crs_display
script = Path(layer_crs_display.__file__).parent / 'tests' / 'native_acceptance.py'
exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'))
```

The script creates temporary input data in an independent project, converts a
point from EPSG:4326 to EPSG:32639 (expected 500000, 0 at longitude 51, latitude 0),
checks a categorical raster and NoData, and verifies unchanged input data.
Do not close QGIS while it is running. If a provider hangs, cancellation may take
time; the test waits for the task to finish before freeing its context.

5. Run small real vector and raster batches through the dialog. Test an existing
   output conflict, cancellation, filtered input, custom suffix, missing source
   CRS and a transformation requiring a locally installed datum grid.
6. Record QGIS, Qt, GDAL and OS versions, results and any traceback. Do not mark
   untested platforms or versions as passed. Add authentic screenshots only after
   the interface has been exercised in native QGIS.

## Current status

Native QGIS/GDAL testing is pending. The declared 3.22–3.x metadata range is
inherited from the supplied version and is not a tested-platform matrix.
