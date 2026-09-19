# SPDX-License-Identifier: GPL-2.0-or-later
"""Portable naming and output planning. No GIS objects or data edits."""
from collections import Counter
import errno
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata

INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)
SIDECARS = ('.aux.xml', '.ovr', '.msk', '-wal', '-shm', '-journal')


def publish_file(source, final):
    """Publish a staged file without overwriting an existing destination."""
    source = Path(source)
    final = Path(final)
    fd = os.open(str(final), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    os.close(fd)
    transfer = None
    try:
        try:
            os.replace(str(source), str(final))
        except OSError as exc:
            if exc.errno != errno.EXDEV:
                raise
            fd, transfer_name = tempfile.mkstemp(
                prefix="." + final.name + ".",
                suffix=".part",
                dir=str(final.parent),
            )
            os.close(fd)
            transfer = Path(transfer_name)
            shutil.copy2(str(source), str(transfer))
            os.replace(str(transfer), str(final))
            try:
                source.unlink()
            except OSError:
                # The private stage cleanup retries delayed provider locks.
                pass
    except Exception:
        final.unlink(missing_ok=True)
        if transfer is not None:
            transfer.unlink(missing_ok=True)
        raise


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


def geopackage_filename(value):
    value = str(value).strip()
    if not value or value in ('.', '..') or INVALID.search(value) or value.endswith((' ', '.')):
        raise ValueError('Enter a GeoPackage filename without a folder path.')
    if not value.lower().endswith('.gpkg'):
        value += '.gpkg'
    if RESERVED.match(value) or len(value.encode('utf-8')) > 200:
        raise ValueError('The GeoPackage filename is reserved or too long.')
    return value


def plan_outputs(items, folder, suffix, gpkg_name='reprojected.gpkg'):
    folder = Path(folder)
    existing = {path_key(p.name) for p in folder.iterdir()} if folder.is_dir() else set()
    rows = []
    for item in items:
        row = dict(item)
        try:
            row['output_name'], filename = output_names(item['name'], suffix, item['kind'])
            row['output_layer'] = ''
            if item['kind'] == 'vector':
                row['output_layer'] = filename[:-5]
                if row['output_layer'].lower().startswith(('gpkg_', 'sqlite_', 'rtree_')):
                    row['output_layer'] = '_' + row['output_layer']
                filename = geopackage_filename(gpkg_name)
            row['output_path'] = str(folder / filename)
            row['error'] = 'An output file or its sidecar already exists in the destination folder.' if any(path_key(filename+s) in existing for s in ('',)+SIDECARS) else ''
            row['filename'] = filename
        except ValueError as exc:
            row.update(output_name='', output_path='', output_layer='', filename='', error=str(exc))
        rows.append(row)
    def key(row):
        return path_key(row['filename']), path_key(row['output_layer'])
    counts = Counter(key(r) for r in rows if r['filename'])
    for row in rows:
        if row['filename'] and counts[key(row)] > 1:
            row['error'] = 'Selected layers have duplicate output names. Reproject one separately with another suffix.'
    return rows
