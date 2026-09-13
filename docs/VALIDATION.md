# Validation of release 0.7.1

- PASS: the maintainer confirmed that the 0.7.0 package functions in both
  QGIS 3 and QGIS 4.
- PASS: 0.7.1 changes only the version, stable metadata and validation records;
  runtime compatibility and processing behavior are identical to 0.7.0.
- PASS: metadata and runtime version agree at 0.7.1, the declared range remains
  QGIS 3.22–4.x and `experimental=False` is set.
- PASS: 13 portable tests, real PyQt5 interface/batch lifecycle tests, Python
  compilation and reproducible installation-archive construction.
- RECORD STILL REQUIRED: exact QGIS, Qt, Python, GDAL and OS versions and the
  output of the complete native acceptance script for each tested environment.

# Validation of candidate 0.7.0

- PASS: metadata and runtime version agree at 0.7.0; the declared range is
  QGIS 3.22–4.x and `experimental=True` remains set.
- PASS: 13 portable output-planning and collision tests.
- PASS: the real PyQt5 interface/batch lifecycle suite at three dialog sizes,
  including toolbar state, widget migration, success/failure, cancellation,
  shared GeoPackage behavior, same-CRS exclusion and raster parameters.
- PASS: every runtime import uses the QGIS-provided `qgis.PyQt` layer. Qt and
  QGIS enum references use their scoped forms; `QAction` has Qt6 and Qt5 import
  paths; dialog loops use `exec()`.
- PASS: the QGIS 3 fallback and the QGIS 4.2 `Qgis.InvalidGeometryCheck`
  member names are handled separately.
- PASS: Python compilation, installation-archive integrity, one-directory ZIP
  layout and reproducible release construction.
- PASS: comparison with 0.6.1 shows only compatibility API substitutions,
  version/compatibility labels and documentation changes; processing logic and
  feature behavior are unchanged.
- NOT RUN in this build environment: native QGIS 4/Qt6 loading and Processing/
  GDAL acceptance. The QGIS repository's `pyqgis4-checker` will also run only
  after upload.
- NOT REPEATED: the complete native QGIS 3 Processing/GDAL acceptance suite.
  The maintainer has reported successful functional checks of 0.6.1 in QGIS 3.

Keep 0.7.0 experimental until the same native acceptance procedure passes and
the exact environment is recorded independently for QGIS 3 and QGIS 4.

## Previous checks

# Validation of candidate 0.6.1

- PASS: 13 portable tests and real PyQt5 interface checks at three dialog sizes.
- PASS: the toolbar starts in icon-only mode and restores icon-only mode after
  a simulated global change to Text Beside Icon. Both actual tool buttons retain
  their 28 px icons, stable object names and permanent boxed styling.
- PASS: the plugin icon and three toolbar states use uniquely named 0.6.1 SVG
  assets, avoiding reuse of the earlier Qt icon-cache keys.
- PASS: all eleven bundled SVG assets parse as valid XML.
- PASS: Python syntax, Flake8 7.3.0 on the changed plugin/About modules and E731
  across all runtime code.
- Reprojection code and the declared QGIS 3 compatibility range are unchanged.
- A full QGIS restart remains part of the installation check because Python
  plugin modules already loaded by the application cannot be replaced in place.

# Validation of candidate 0.6.0

- PASS: 13 portable naming and output-planning tests.
- PASS: real PyQt5 interface checks at three batch-dialog sizes, plus the new
  About dialog. Each project, social and email destination was exercised with
  an injected URL opener; the test made no network request or browser launch.
- PASS: toolbar checks confirm icon-only buttons at 28 px, permanent boxed
  button styling, distinct Display CRS on/off icons and the active green state.
- PASS: all seven bundled SVG assets parse as valid XML. Visual checks confirm
  readable toolbar boxes in both Display CRS states and branded social glyphs
  in the About dialog.
- PASS: Python syntax and release-package structure checks. The installation ZIP
  contains one top-level plugin directory and excludes development tests.
- PASS: extracted installation ZIP, Bandit 1.9.4 default rules: zero findings,
  zero scan errors and no rule suppressions.
- PASS: Flake8 7.3.0 on the changed plugin/About modules and E731 across all
  runtime code.
- Reprojection code and declared QGIS 3 compatibility are unchanged.
- No new native QGIS/GDAL test is claimed for this interface-only update.

# Validation of candidate 0.5.4

- PASS: extracted installation ZIP, Flake8 7.3.0 E731 check: zero findings.
- PASS: extracted installation ZIP, Bandit 1.9.4 default rules: zero findings
  and zero scan errors, without rule suppressions.
- PASS: Python syntax of every installed Python file.
- Only the layer-loading helper syntax changed; output behavior is unchanged.
- No new native QGIS test run was performed for this small refactor.
- The portal's 48 Qt6 migration findings remain outside this QGIS 3 release.
  Do not treat a clean security scan as proof of QGIS 4 compatibility.

# Validation of candidate 0.5.3

- Reproduced the uploaded 0.5.2 scan locally with Bandit 1.9.4: 9 Python
  files, 26 B101 findings, all in tests/native_acceptance.py.
- Scanned the extracted 0.5.3 installation ZIP with default Bandit rules and
  no suppressions: 8 Python files, 0 findings, 0 scan errors.
- Runtime Python files match 0.5.2 byte-for-byte except PLUGIN_VERSION.
- Development tests remain in the public repository; the installed plugin
  does not import or require them. Installation instructions now point to
  the repository copy of the native acceptance script.
- The maintainer reported a successful basic QGIS check of 0.5.2; exact
  QGIS/OS versions and the full native acceptance suite remain unrecorded.
- This is a QGIS 3 release. Qt6/QGIS 4 compatibility has not been implemented.
- The QGIS portal must scan and review the new version after upload; a local
  Bandit pass does not guarantee portal approval or cover its other checks.

## Previous functional checks

# Validation of candidate 0.5.2

- PASS: 13 portable naming/planning tests, including one shared GeoPackage,
  distinct table names, custom filenames, reserved names and collision handling.
- PASS: real PyQt5 widgets at 360x240, 640x360 and 1024x600.
- PASS with simulated GIS boundaries: two converted vectors share one file with
  distinct layer URIs; explicitly queued same-CRS layers are skipped; an all-same
  batch creates no GeoPackage; unequal coordinate epochs are not treated as equal.
- PASS with simulated GIS boundaries: reprojection failure continuation, CRS/count
  validation, packaging failure, incomplete packaging, cancellation during
  conversion/staging/packaging, late destination collision and source preservation.
- PASS with simulated GIS boundaries: raster task parameters and GeoTIFF output.
- PASS: widget migration preserves unrelated embedded widgets.
- NOT RUN: native QGIS/GDAL package writing and real CRS alias equivalence,
  coordinate transformation, actual plugin load/unload, Windows/macOS behavior,
  and the QGIS repository security scan.

The native acceptance script now checks real reprojection of two vectors into
one GeoPackage, exact table membership, same-CRS exclusion, CRS aliases, raster
values/NoData and unchanged inputs. Run it inside QGIS before claiming native
compatibility. These automated checks do not constitute QGIS approval.
