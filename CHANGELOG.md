# 0.6.0 — GeoForge links (experimental)

- Replace the plain About message with a dedicated plugin information dialog.
- Add direct links to the official QGIS plugin page, source repository, issue
  tracker and GeoForge Studio email.
- Add the supplied GeoForge Studio LinkedIn, Instagram and Telegram pages.
- Keep reprojection behavior and the declared QGIS 3 compatibility range unchanged.

# 0.5.4 — code quality fix (experimental)

- Replace the assigned layer-loading lambda with a named function (Flake8 E731).
- Keep output behavior and the declared QGIS 3 compatibility range unchanged.
- The separately reported Qt6 migration findings are not addressed by this release;
  QGIS 4 support still requires migration and native testing.

# 0.5.3 — installation packaging fix (experimental)

- Keep the native acceptance script in the source repository, outside the installed plugin.
- Remove development-only test code from the installation ZIP. The QGIS scan of
  0.5.2 reported 26 Bandit B101 findings in this test script.
- Update the instructions for running native tests from a repository checkout.
- Runtime behavior is unchanged from 0.5.2, apart from the reported version.
- Continue targeting QGIS 3; this release does not claim Qt6/QGIS 4 support.

# 0.5.2 — shared GeoPackage (experimental)

- Save converted vector layers to separate tables in one configurable GeoPackage.
- Exclude layers already in the target CRS at selection and execution time; compare equivalent CRS definitions through GDAL when QGIS equality is insufficient.
- Keep raster outputs as GeoTIFF and leave original inputs untouched.
- Package only validated converted vectors, with related-layer export disabled.
- Validate every packaged layer before publication; prevent overwriting existing files.
- Discard unsaved vector outputs on cancellation; keep already published rasters.
- Add regression checks for shared outputs, skipped layers, package failures and late collisions.
- Native QGIS acceptance remains pending.

# 0.5.1 — publication preparation (experimental)

- Use GeoForge Studio as the public maintainer identity.
- Use neutral settings, toolbar and widget identifiers. Preferences reset once;
  older CRS widget entries are removed when the new display is enabled/disabled.
- Add proposed GPL-2.0-or-later licensing, public documentation and metadata URLs.
- Move tests outside the runtime package and add a reproducible ZIP builder.
- Mark this candidate experimental pending native QGIS acceptance.
- Set the public contact email supplied by the maintainer.
- The reprojection engine and dialog workflow are unchanged from 0.5.0.

# 0.5.0

- Redesigns the English batch window with destination and layer cards.
- Adds layer/CRS search and explicit counts of selected layers hidden by search.
- Moves optional resampling and project settings into a collapsible Advanced options section.
- Keeps progress, Stop, Close and Reproject in a persistent footer.
- Adds naming examples, readiness guidance and coloured per-layer results.
- Checks layout at three window sizes, search semantics and advanced option toggling using Qt with simulated GIS boundaries.

# 0.4.2

- Restores an English-only interface, messages and user guide.
- Uses left-to-right layout with Display CRS followed by Reproject.
- Adds distinct layer/eye and globe/arrow toolbar icons.

# 0.4.1

- Groups Display and Convert in one dedicated CRS toolbar, with Persian labels and distinct icons.
- Removes the toolbar and its actions cleanly on unload.

# 0.4.0

- Preserves 0.3.0 CRS embedded widgets and display settings.
- Adds scrollable batch dialog: target CRS, selected layers, one output folder and suffix-only display names.
- Uses native:reprojectlayer and gdal:warpreproject via background Processing tasks.
- Adds duplicate/existing filename checks, staged publication, cancellation, per-layer failures and JSON reports.
- Adds optional loading, source visibility and project CRS controls.
- Portable and real-Qt boundary tests included; native QGIS acceptance script supplied but not run here.

# Changelog

## 0.3.0

- Added a dark gray rounded border around the white toolbar icon.
- Kept the centered bold black `CRS` label and all plugin behavior unchanged.

## 0.2.0

- Changed all user-facing content and documentation to English.
- Replaced the icon with bold black `CRS` text on a white background.
- Removed all project CRS comparison logic and related warnings.
- The widget now reports only the current CRS assigned to each layer.

## 0.1.0

- Initial release.
