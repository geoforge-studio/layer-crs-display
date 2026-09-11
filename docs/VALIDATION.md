# Validation of candidate 0.5.1

- PASS: all 9 portable naming/collision tests.
- PASS: real PyQt5 widgets at 360x240, 640x360 and 1024x600.
- PASS with simulated GIS boundaries: batch success, continued processing after a
  failure, output CRS/count checks, reported transformation errors, cancellation,
  collision protection, source preservation and raster task parameters.
- PASS: old CRS widget IDs are replaced without duplicating the new widget ID;
  unrelated widget IDs are preserved.
- PASS: Python syntax compilation.
- PASS: repeat builds produce identical ZIP bytes; runtime files in ZIP match source.
- PASS: one top-level installation directory, required icon and documentation,
  no bytecode/caches/binaries, and no previous personal identifiers in text source.
- PASS: the reprojection engine AST is unchanged from the supplied 0.5.0 version.
- PASS: the release builder accepts complete metadata; the earlier empty-email
  draft was correctly blocked.
- NOT RUN: native QGIS/GDAL, real coordinate transformation, actual QGIS plugin
  load/unload, native Windows/macOS behavior, QGIS repository security scan.
- The public repository and Issues endpoint were verified before source upload;
  native QGIS approval remains a separate step.

The checks above support local testing of this candidate. They do not constitute
QGIS approval or a guarantee of compatibility with the declared version range.
