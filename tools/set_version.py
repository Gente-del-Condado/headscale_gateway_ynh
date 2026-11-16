#!/usr/bin/env python3
"""Establece o comprueba la versión común exigida por los manifiestos de plataforma."""
import argparse
import json
from pathlib import Path
import re
import tomllib
from yunohost_metadata import readme as yunohost_readme
from android_version import release_version

ROOT = Path(__file__).resolve().parents[1]


def mobile_documents(root, check=False):
    """Las versiones visibles de las guías proceden del mismo cálculo que la APK."""
    label, code = release_version(root)
    replacements = {
        'android/README.md': [(r'La entrega común \*\*[^*]+\*\* utiliza el motor Go compartido y `versionCode`\n`[0-9]+`',
                               f'La entrega común **{label}** utiliza el motor Go compartido y `versionCode`\n`{code}`')],
        'packaging/android/play/PUBLICACION.md': [(r'(?m)^# Preparación de Google Play · .+$', f'# Preparación de Google Play · {label}'),
            (r'(?m)^- Versión: `[^`]+`; versionCode: `[0-9]+`;', f'- Versión: `{label}`; versionCode: `{code}`;')],
    }
    for relative, changes in replacements.items():
        path = root / relative
        original = text = path.read_text()
        for pattern, value in changes:
            text, count = re.subn(pattern, lambda _: value, text)
            if count != 1:
                raise ValueError('No se reconoce la versión de la guía: ' + relative)
        if check:
            if original != text:
                raise ValueError('Versión documental obsoleta: ' + relative)
        else:
            path.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    version = args.version or (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        parser.error('Use a version such as 1.2.0')
    hacs = ROOT / 'custom_components/headscale_gateway/manifest.json'
    app = ROOT / 'packaging/homeassistant/config.yaml.in'
    ynh = ROOT / 'packaging/yunohost/manifest.toml'
    desktop = ROOT / 'src/desktop/package.json'
    desktop_lock = ROOT / 'src/desktop/package-lock.json'
    if args.check or not args.version:
        assert (ROOT / 'src/VERSION').read_text().strip() == version
        assert json.loads(hacs.read_text())['version'] == version
        assert re.search(r'^version: (.+)$', app.read_text(), re.M)[1] == version
        assert tomllib.loads(ynh.read_text())['version'].split('~')[0] == version
        assert json.loads(desktop.read_text())['version'] == version
        assert json.loads(desktop_lock.read_text())['version'] == version
        assert json.loads(desktop_lock.read_text())['packages']['']['version'] == version
        assert (ROOT / 'packaging/yunohost/README.md').read_text() == yunohost_readme(ROOT)
        mobile_documents(ROOT, check=True)
    else:
        previous = (ROOT / 'VERSION').read_text().strip()
        # Los ejemplos instalables deben acompañar a la versión de sus paquetes.
        for guide in ('packaging/linux/README.md', 'packaging/flatpak/README.md'):
            path = ROOT / guide
            path.write_text(path.read_text().replace(previous, version))
        manifest = json.loads(hacs.read_text()); manifest['version'] = version
        hacs.write_text(json.dumps(manifest, indent=2) + '\n')
        app.write_text(re.sub(r'^version: .+$', 'version: ' + version, app.read_text(), flags=re.M))
        ynh.write_text(re.sub(r'^version = ".+"$', 'version = "' + version + '~ynh1"', ynh.read_text(), flags=re.M))
        (ROOT / 'VERSION').write_text(version + '\n')
        (ROOT / 'src/VERSION').write_text(version + '\n')
        package = json.loads(desktop.read_text()); package['version'] = version
        desktop.write_text(json.dumps(package, indent=2) + '\n')
        lock = json.loads(desktop_lock.read_text())
        lock['version'] = lock['packages']['']['version'] = version
        desktop_lock.write_text(json.dumps(lock, indent=2) + '\n')
        (ROOT / 'packaging/yunohost/README.md').write_text(yunohost_readme(ROOT))
        mobile_documents(ROOT)
    print('Release version: ' + version)


if __name__ == '__main__':
    main()
