# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure text-formatting helpers used by the QGIS widget."""

from html import escape


VALID_FORMATS = ("authid", "authid_name", "name")


def clean_text(value):
    """Return a stripped text value without exposing None."""
    return "" if value is None else str(value).strip()


def shorten(text, limit=58):
    """Shorten long CRS descriptions for the Layers panel."""
    text = clean_text(text)
    if limit < 2 or len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def display_text(auth_id, description, display_format="authid"):
    """Build the compact label shown in the layer tree."""
    display_format = (
        display_format if display_format in VALID_FORMATS else "authid"
    )
    auth_id = clean_text(auth_id)
    description = clean_text(description)

    if not auth_id and not description:
        return "[Undefined CRS]"

    identifier = auth_id or "Custom CRS"
    title = description or identifier

    if display_format == "name":
        return shorten(title)
    if display_format == "authid_name":
        if title == identifier:
            return "[{}]".format(identifier)
        return "[{}] {}".format(identifier, shorten(title, 44))
    return "[{}]".format(identifier)


def tooltip_html(
    layer_name,
    layer_auth_id,
    layer_description,
):
    """Build an escaped HTML tooltip for the layer CRS only."""
    def shown(value, fallback="—"):
        value = clean_text(value)
        return escape(value if value else fallback)

    return (
        "<b>Layer coordinate reference system</b><br>"
        "Layer: {layer}<br>"
        "Authority ID: {layer_id}<br>"
        "CRS name: {layer_crs_name}"
    ).format(
        layer=shown(layer_name),
        layer_id=shown(layer_auth_id),
        layer_crs_name=shown(layer_description),
    )
