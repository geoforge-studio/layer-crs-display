"""Build a deterministic QGIS installation archive using only Python stdlib."""
import argparse
import ast
import configparser
import re
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'layer_crs_display'


def build(release=False):
    metadata = configparser.ConfigParser(interpolation=None)
    metadata.read(PACKAGE / 'metadata.txt', encoding='utf-8')
    info = metadata['general']
    for key in ('name', 'version', 'author', 'description', 'about',
                'qgisMinimumVersion', 'qgisMaximumVersion', 'icon'):
        if not info.get(key, '').strip():
            raise ValueError('Missing metadata: ' + key)
    if not re.fullmatch(r'\d+\.\d+\.\d+', info['version']):
        raise ValueError('Use a three-part numeric version for this builder.')
    if release:
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', info.get('email', '')):
            raise ValueError('Set a working PUBLIC contact email in metadata.txt before submission.')
        for key in ('homepage', 'repository', 'tracker'):
            url = urlsplit(info.get(key, ''))
            if url.scheme != 'https' or not url.netloc:
                raise ValueError('Set a valid HTTPS URL for ' + key)
        if info.get('license') != 'GPL-2.0-or-later':
            raise ValueError('Check the intended license before building a release.')
    sources = [(f, f.relative_to(ROOT).as_posix()) for f in sorted(PACKAGE.iterdir())
               if f.is_file() and f.suffix in ('.py', '.txt', '.svg')]
    sources += [(ROOT / name, 'layer_crs_display/' + name)
                for name in ('README.md', 'LICENSE', 'CHANGELOG.md')]
    sources += [(f, 'layer_crs_display/docs/' + f.name)
                for f in sorted((ROOT / 'docs').glob('*.md'))]
    sources.append((ROOT / 'tests/native_acceptance.py',
                    'layer_crs_display/tests/native_acceptance.py'))
    names = {name for _, name in sources}
    if 'layer_crs_display/' + info['icon'] not in names:
        raise ValueError('The icon is missing from the package.')
    for path, _ in sources:
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    tree = ast.parse((PACKAGE / 'plugin.py').read_text(encoding='utf-8'))
    versions = [node.value.value for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'PLUGIN_VERSION' for t in node.targets)]
    if versions != [info['version']]:
        raise ValueError('Plugin and metadata versions differ.')
    output = ROOT / 'dist' / ('layer_crs_display_' + info['version'] + '.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in sorted(sources, key=lambda item: item[1]):
            entry = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, path.read_bytes())
    if output.stat().st_size > 25 * 1024 * 1024:
        output.unlink()
        raise ValueError('Archive exceeds the QGIS repository size limit.')
    print(output)
    if not release:
        print('LOCAL TEST BUILD: metadata/contact and live links still need publication checks.')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', action='store_true', help='Require complete publication metadata')
    args = parser.parse_args()
    try:
        build(args.release)
    except (ValueError, OSError, KeyError, configparser.Error) as error:
        parser.exit(1, str(error) + '\n')
