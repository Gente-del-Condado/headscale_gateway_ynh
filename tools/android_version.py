"""Versión de entrega Android, independiente de la revisión del motor compartido."""
from pathlib import Path
import re


def release_version(root):
    root = Path(root)
    version = (root / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Versión común no válida')
    properties = (root / 'android/release.properties').read_text()
    values = re.findall(r'^revision=([0-9]+)$', properties, re.M)
    if len(values) != 1 or not 0 <= int(values[0]) <= 9:
        raise ValueError('Revisión Android fuera de 0..9')
    revision = int(values[0])
    major, minor, patch = map(int, version.split('.'))
    code = (major * 1000000 + minor * 1000 + patch) * 10 + revision
    if minor > 999 or patch > 999 or not 0 < code <= 2100000000:
        raise ValueError('La versión no cabe en el código Android')
    return (version + '-android.' + str(revision) if revision > 4 else version), code
