# Layer CRS Display — 0.5.4

Maintainer: GeoForge Studio | QGIS 3.22–3.x (declared range; native validation pending)

The CRS toolbar has two labelled buttons, ordered left to right:

- **Display CRS** (layers and eye): show or hide CRS information in the Layers panel.
- **Reproject** (globe and arrow): open the batch reprojection dialog.

All plugin interface text, tooltips, messages and documentation are in English. Layer names and attribute values retain their original language. When upgrading from a pre-GeoForge build, disable the old version before installing and restart QGIS. Display preferences and the last output folder reset once under the new settings namespace. Older CRS widget entries are replaced; unrelated embedded widgets are retained.

## Quick start

1. Build the installation archive with `python tools/build_zip.py --release` (see below), then install `layer_crs_display_0.5.4.zip` through Plugins → Manage and Install Plugins → Install from ZIP. Restart QGIS.
2. Click **Reproject**. The target CRS initially follows the project CRS and can be changed.
3. Choose one output folder, a GeoPackage filename (default `reprojected.gpkg`) and a layer name suffix, such as `_UTM39`. `Roads` becomes `Roads_UTM39`. No numbering or prefix is automatically added.
4. Eligible layers with a different CRS are initially selected. Use **Use panel selection** to use the Layers panel selection, or change checkboxes individually.
5. Review the output names and click **Reproject**. Progress and the result for each layer are displayed.

## Batch window

**Set the destination** groups the target CRS, output folder, shared GeoPackage filename and layer suffix, with a live output naming example. **Choose the layers** provides a searchable table, selection controls, output previews and per-layer status.

Search filters the visible list without changing selection. The summary explicitly counts selected layers hidden by search. Selection buttons apply to all layers, including hidden search results.

**Advanced options** expands to show raster resampling, adding outputs, hiding originals and changing the project CRS. Defaults are unchanged. Progress and the Reproject, Stop and Close buttons stay visible in a fixed footer while the form scrolls. Readiness guidance explains what must be completed before starting.

## Outputs and scope

- All successfully converted vector layers are saved as separate named tables in **one GeoPackage** (`reprojected.gpkg` by default). Each converted raster is saved to a GeoTIFF. Layers already in the target CRS produce no copy and are excluded from the package.
- Coordinates are reprojected, rather than merely assigning a different CRS label.
- Source data, coordinates and layer names are retained. Adding outputs, hiding source layers and changing the project CRS are separate options.
- Existing files are not overwritten. If selected layers have duplicate output names, run one separately with another suffix. The displayed name is exactly the original name plus suffix; invalid filesystem characters are replaced with `_` in the physical raster filename or GeoPackage table name. Reserved GeoPackage table prefixes are escaped with `_`. The shared GeoPackage filename can be changed independently of the layer suffix.
- All features matching the current layer filter are exported. Selecting individual features does not restrict the export. The source filter is recorded in the report. GeoPackage internal feature IDs may be regenerated; use an attribute field for stable business identifiers.
- Attribute field names and values are transferred by the reprojection algorithm. A reported transformation error or a feature-count mismatch prevents publication of that layer's output. Styles are copied where possible; project forms, relationships and other dependencies are not fully migrated.

## Rasters and performance

Nearest neighbour is the default for categorical values. Choose bilinear or cubic for continuous data such as elevation. The chosen method applies to all rasters in that batch; use separate batches when different methods are needed.

GDAL calculates output cell size and extent. Input data type and source NoData are inherited through the algorithm. Matching CRS does not guarantee matching resolution, extent or grid alignment. TIFF outputs are tiled and uncompressed, with BigTIFF enabled when needed; output files can be large.

Layers run sequentially as background tasks; validated vector outputs are then combined by `native:package` in another background task. Temporary vector data is removed after completion. Processing is sequential to limit simultaneous memory and disk use. Raster Warp enables overlapping I/O and processing and uses up to four computation threads. Actual speed depends on data volume, drivers, storage and transformation; no benchmark or time guarantee is claimed.

## Requirements and exclusions

- Unknown source CRS: assign the actual source CRS first. The plugin does not guess it.
- Edit mode: save changes and leave edit mode before reprojection.
- Layers already in the target CRS are listed but not exported again. The check uses QGIS equality and GDAL full-CRS equivalence for aliases, retaining coordinate epoch distinctions. Same zone alone does not imply the same CRS.
- Non-spatial tables, WMS/XYZ services, meshes and point clouds are not supported. Rasters must use the GDAL provider. Readable GeoPackage/FileGDB raster sublayers depend on the GDAL version bundled with QGIS.
- Processing must be enabled; raster conversion also requires its GDAL provider. No additional pip dependencies are required.
- Transformations needing datum grids require the appropriate grids and coordinate operation in QGIS. The plugin does not download them or verify that the assigned source CRS is correct.

## Cancellation and reporting

**Stop** cancels the current operation and remaining queue. Already saved rasters are retained. Converted vectors are staged and saved together only when packaging succeeds; stopping before that point discards the unsaved vector outputs. A failed or cancelled package is never exposed under the final filename. The dialog cannot close until cancellation completes. Failure of one layer does not stop subsequent layers. A JSON report in the output folder records source and target CRS, names, filters, statuses and errors.

## Development and validation

This repository contains the unpacked plugin source, tests and a reproducible ZIP builder.
The installable ZIP has one top-level directory: `layer_crs_display/`.

Run from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q layer_crs_display tests tools
# Optional UI/batch lifecycle tests; PyQt5 is a test-only dependency:
QT_QPA_PLATFORM=offscreen python tests/qt_batch_acceptance.py
# Build a local testing ZIP (does not require a public contact email):
python tools/build_zip.py
```

The portable suite checks output names and collisions. The Qt suite uses real
widgets and files but simulated QGIS objects, providers and tasks. It checks
three dialog sizes, selection/search, success/failure, CRS/count validation,
cancellation, shared-package failures, same-CRS exclusion and preservation of existing outputs. These tests do **not** prove
that QGIS/GDAL performs reprojection correctly.

Development tests stay in the source repository and are excluded from the installation ZIP. Download the repository for the installed version, then run `tests/native_acceptance.py` inside the Python Console of an actual QGIS 3
installation with this plugin installed and Processing/GDAL enabled. It generates
small temporary vector/raster fixtures and checks transformed coordinates,
attributes, categorical values, NoData and source preservation. See
[testing instructions](docs/TESTING.md). Native testing is still pending; do not
claim compatibility with a QGIS version until it has been tested.

## Publication status

Version 0.5.4 is an **experimental release candidate**, not an approved QGIS plugin.
Source code and support are hosted at
[geoforge-studio/layer-crs-display](https://github.com/geoforge-studio/layer-crs-display).
The public contact email is `reynolds.mach88@gmail.com`. Native QGIS acceptance
is still pending; see the [publication checklist](docs/PUBLISHING.md).

Build the installation archive from this source:

```bash
python tools/build_zip.py --release
```

This command validates required metadata and builds the archive. It does not
contact GitHub or QGIS and cannot prove that the links are live or the plugin works.

## License

This project is distributed under **GNU GPL version 2 or any later version**
(`GPL-2.0-or-later`); see [LICENSE](LICENSE). No third-party binary files are bundled.

## Support

Use the repository's Issues tab to report problems. Include QGIS/OS/Python
versions, layer/provider type, source and target CRS, the error message and a
minimal non-sensitive example. Do not post private datasets. JSON batch reports
contain layer names, file paths and subset filters; redact sensitive content before
sharing a report.

## Implementation references

- https://docs.qgis.org/3.22/en/docs/pyqgis_developer_cookbook/tasks.html
- https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/qgis/vectorgeneral.html#reproject-layer
- https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/gdal/rasterprojections.html#warp-reproject

- https://docs.qgis.org/3.40/en/docs/user_manual/processing_algs/qgis/database.html#package-layers
- https://gdal.org/en/stable/api/python/spatial_ref_api.html
