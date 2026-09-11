# SPDX-License-Identifier: GPL-2.0-or-later
"""Portable naming and output planning. No GIS objects or data edits."""
from collections import Counter
from pathlib import Path
import re
import unicodedata

INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)
SIDECARS = ('.aux.xml', '.ovr', '.msk', '-wal', '-shm', '-journal')


def output_names(layer_name, suffix, kind):
    if not suffix or not suffix.strip():
        raise ValueError('Enter an output name suffix, such as _UTM39.')
    if INVALID.search(suffix) or suffix.endswith((' ', '.')):
        raise ValueError('The suffix contains an invalid filename character.')
    display = str(layer_name) + suffix
    stem = INVALID.sub('_', display).rstrip(' .')
    if not stem:
        raise ValueError('The output name is empty.')
    if RESERVED.match(stem):
        stem = '_' + stem
    if len(stem.encode('utf-8')) > 200:
        raise ValueError('The filename is too long. Shorten the source name or suffix.')
    if kind not in ('vector', 'raster'):
        raise ValueError('This layer type is not supported for reprojection.')
    return display, stem + ('.gpkg' if kind == 'vector' else '.tif')


def path_key(name):
    # Windows and macOS may compare case/Unicode differently from Linux.
    return unicodedata.normalize('NFC', str(name)).casefold()


def plan_outputs(items, folder, suffix):
    folder = Path(folder)
    existing = {path_key(p.name) for p in folder.iterdir()} if folder.is_dir() else set()
    rows = []
    for item in items:
        row = dict(item)
        try:
            row['output_name'], filename = output_names(item['name'], suffix, item['kind'])
            row['output_path'] = str(folder / filename)
            row['error'] = 'An output file or its sidecar already exists in the destination folder.' if any(path_key(filename+s) in existing for s in ('',)+SIDECARS) else ''
            row['filename'] = filename
        except ValueError as exc:
            row.update(output_name='', output_path='', filename='', error=str(exc))
        rows.append(row)
    counts = Counter(path_key(r['filename']) for r in rows if r['filename'])
    for row in rows:
        if row['filename'] and counts[path_key(row['filename'])] > 1:
            row['error'] = 'Selected layers have duplicate output names. Reproject one separately with another suffix.'
    return rows
