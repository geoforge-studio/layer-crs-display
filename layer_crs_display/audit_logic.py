# SPDX-License-Identifier: GPL-2.0-or-later
"""Portable CRS audit classification and summary helpers."""

STATUS_OK = "OK"
STATUS_DIFFERENT = "Different"
STATUS_MISSING = "Missing"
STATUSES = (STATUS_OK, STATUS_DIFFERENT, STATUS_MISSING)


def classify_crs(source_valid, equivalent_to_project):
    """Return the three-state audit result without changing any CRS."""
    if not source_valid:
        return STATUS_MISSING
    return STATUS_OK if equivalent_to_project else STATUS_DIFFERENT


def audit_summary(rows):
    """Count layers, distinct valid CRS definitions and status totals."""
    rows = list(rows)
    fingerprints = {
        row.get("crs_key")
        for row in rows
        if row.get("status") != STATUS_MISSING and row.get("crs_key")
    }
    return {
        "layers": len(rows),
        "crs": len(fingerprints),
        "ok": sum(row.get("status") == STATUS_OK for row in rows),
        "different": sum(
            row.get("status") == STATUS_DIFFERENT for row in rows
        ),
        "missing": sum(
            row.get("status") == STATUS_MISSING for row in rows
        ),
    }


def matches_filter(row, status_filter):
    """Return whether an audit row belongs in the selected status view."""
    return status_filter == "All" or row.get("status") == status_filter


def reprojectable_layer_ids(rows, selected_layer_ids):
    """Keep selected Different layers in audit order; never include Missing."""
    selected = set(selected_layer_ids)
    return [
        row["layer_id"]
        for row in rows
        if row.get("status") == STATUS_DIFFERENT
        and row.get("layer_id") in selected
    ]
