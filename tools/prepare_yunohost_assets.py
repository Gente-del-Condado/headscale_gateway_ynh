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


def remote_target(repository, reference):
    """Resuelve también etiquetas anotadas, sin mover referencias publicadas."""
    output = subprocess.check_output(['git', '-C', str(repository), 'ls-remote',
                                      'origin', reference, reference+'^{}'], text=True)
    references = {ref: commit for commit, ref in (line.split() for line in output.splitlines())}
    return references.get(reference+'^{}') or references.get(reference)


def request(repository):
    """La rama pública ya debe contener las fuentes aprobadas por la revisión."""
    version = (ROOT/'VERSION').read_text().strip()
    public = (remote_target(repository, 'refs/tags/server-v'+version)
              or remote_target(repository, 'refs/heads/upstream-source'))
    if not public:
        raise ValueError('Faltan los fuentes públicos del motor')
    payload = ROOT/'yunohost/payload'
    names = ('headscale-gateway-linux-amd64', 'headscale-gateway-linux-arm64', 'source.tar.gz')
    return {'format': 1, 'version': version,
            'source_commit': public,
            'sha256': {name: digest(payload/name)
                       for name in names}}


def ensure_server_tag(repository, data):
    """Forgejo debe conservar la etiqueta antes de crear una release en su réplica."""
    reference = 'refs/tags/server-v'+data['version']
    existing = remote_target(repository, reference)
    if existing:
        if existing != data['source_commit']:
            raise ValueError('La etiqueta del motor ha cambiado durante la publicación')
        return
    subprocess.run(['git', '-C', str(repository), 'fetch', '--no-tags', 'origin',
                    'refs/heads/upstream-source'], check=True)
    fetched = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'FETCH_HEAD'], text=True).strip()
    if fetched != data['source_commit']:
        raise ValueError('Los fuentes públicos han cambiado durante la publicación')
    subprocess.run(['git', '-C', str(repository), 'push', 'origin',
                    data['source_commit']+':'+reference], check=True)


def prepare(repository):
    repository = Path(repository).resolve()
    data = request(repository)
    ensure_server_tag(repository, data)
    target = repository/WORKFLOW
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'packaging/yunohost'/WORKFLOW, target)
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
