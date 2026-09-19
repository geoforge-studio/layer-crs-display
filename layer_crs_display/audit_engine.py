# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only extraction of CRS audit details from QGIS layers."""

from qgis.core import QgsUnitTypes

from .audit_logic import classify_crs
from .batch_engine import same_crs


def _enum_name(value):
    name = getattr(value, "name", "")
    if callable(name):
        name = name()
    return str(name or "")


def crs_type_name(crs):
    if not crs.isValid():
        return ""
    try:
        type_name = _enum_name(crs.type())
        if "Geographic" in type_name:
            return "Geographic"
        if "Projected" in type_name:
            return "Projected"
        if type_name:
            return type_name.replace("Crs", "").replace("2d", " 2D")
    except (AttributeError, RuntimeError, TypeError):
        pass
    try:
        return "Geographic" if crs.isGeographic() else "Projected"
    except (AttributeError, RuntimeError):
        return ""


def crs_unit_name(crs):
    if not crs.isValid():
        return ""
    try:
        return str(QgsUnitTypes.toString(crs.mapUnits()))
    except (AttributeError, RuntimeError, TypeError):
        return ""


def crs_datum_name(crs):
    if not crs.isValid():
        return ""
    try:
        datum = crs.datumEnsemble()
        name = datum.name()
        if name:
            return str(name)
    except (AttributeError, RuntimeError, TypeError):
        pass
    try:
        from osgeo import osr

        reference = osr.SpatialReference()
        if reference.ImportFromWkt(crs.toWkt()) == 0:
            for key in ("ENSEMBLE", "DATUM"):
                name = reference.GetAttrValue(key)
                if name:
                    return str(name).replace("_", " ")
    except (ImportError, AttributeError, RuntimeError, TypeError):
        pass
    return ""


def crs_label(crs):
    if not crs.isValid():
        return ""
    return str(crs.authid() or crs.description() or "Custom CRS")


def crs_key(crs):
    if not crs.isValid():
        return ""
    return str(crs.authid() or crs.toWkt()).strip()


def audit_layer(layer, reference_crs):
    """Return a display record for one layer without mutating it."""
    crs = layer.crs()
    valid = bool(crs.isValid())
    equivalent = bool(
        valid and reference_crs.isValid() and same_crs(crs, reference_crs)
    )
    return {
        "layer_id": layer.id(),
        "name": layer.name(),
        "status": classify_crs(valid, equivalent),
        "crs": crs_label(crs),
        "crs_key": crs_key(crs),
        "type": crs_type_name(crs),
        "datum": crs_datum_name(crs),
        "unit": crs_unit_name(crs),
    }


def scan_project(project, reference_crs):
    """Scan layers once in layer-tree order and return audit records."""
    rows = []
    seen = set()
    for node in project.layerTreeRoot().findLayers():
        layer = node.layer()
        if layer is None or layer.id() in seen:
            continue
        rows.append(audit_layer(layer, reference_crs))
        seen.add(layer.id())
    return rows
