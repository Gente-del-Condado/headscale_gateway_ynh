#!/usr/bin/env python3
"""Prepara recursos públicos verificables antes de actualizar el paquete YunoHost."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = '.github/workflows/server-assets.yml'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def request(repository):
    """La rama pública ya debe contener las fuentes aprobadas por la revisión."""
    public = subprocess.check_output(['git', '-C', str(repository), 'ls-remote',
                                     'origin', 'refs/heads/upstream-source'], text=True).split()[0]
    payload = ROOT/'yunohost/payload'
    names = ('headscale-gateway-linux-amd64', 'headscale-gateway-linux-arm64', 'source.tar.gz')
    return {'format': 1, 'version': (ROOT/'VERSION').read_text().strip(),
            'source_commit': public,
            'sha256': {name: digest(payload/name)
                       for name in names}}


def prepare(repository):
    repository = Path(repository).resolve()
    target = repository/WORKFLOW
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'packaging/yunohost'/WORKFLOW, target)
    data = request(repository)
    (repository/'release-request.json').write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    return data


def verify(data, timeout=900):
    """Una versión instalable solo se publica después de verificar sus descargas."""
    version = data['version']
    base = f'https://github.com/Gente-del-Condado/headscale_gateway_ynh/releases/download/server-v{version}/'
    deadline = time.monotonic()+timeout
    pending = dict(data['sha256'])
    while pending:
        for name, digest in list(pending.items()):
            try:
                with urllib.request.urlopen(base+name, timeout=60) as response:
                    actual = hashlib.file_digest(response, 'sha256').hexdigest()
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                continue
            if actual != digest:
                raise ValueError('El recurso público no corresponde a los fuentes aprobados: '+name)
            del pending[name]
        if pending:
            if time.monotonic() >= deadline:
                raise TimeoutError('Los recursos públicos aún no están disponibles: '+', '.join(pending))
            time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(json.loads((args.repository/'release-request.json').read_text()))
        print('Recursos públicos descargados y verificados por SHA-256.')
    else:
        prepare(args.repository)
        print('Petición de recursos preparada; todavía no se ha cambiado el paquete instalable.')


if __name__ == '__main__':
    main()
