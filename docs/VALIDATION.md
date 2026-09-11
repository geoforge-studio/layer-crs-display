# Validation of candidate 0.5.4

- PASS: extracted installation ZIP, Flake8 7.3.0 E731 check: zero findings.
- PASS: extracted installation ZIP, Bandit 1.9.4 default rules: zero findings
  and zero scan errors, without rule suppressions.
- PASS: Python syntax of every installed Python file.
- Only the layer-loading helper syntax changed; output behavior is unchanged.
- No new native QGIS test run was performed for this small refactor.
- The portal's 48 Qt6 migration findings remain outside this QGIS 3 release.
  Do not treat a clean security scan as proof of QGIS 4 compatibility.

## Previous checks

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
