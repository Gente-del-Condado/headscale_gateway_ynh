#!/usr/bin/env python3
"""Publica los recursos comprobados de YunoHost directamente en GitHub."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

from publish_yunohost_repo import validate_package

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'Gente-del-Condado/headscale_gateway_ynh'
NAMES = ('headscale-gateway-linux-amd64', 'headscale-gateway-linux-arm64', 'source.tar.gz')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def gh(*arguments):
    """La credencial llega mediante GH_TOKEN, nunca en argumentos ni registros."""
    return subprocess.run(['gh', *arguments], check=True, capture_output=True, text=True).stdout


def api(path):
    return json.loads(gh('api', f'repos/{REPOSITORY}/'+path))


def verify_downloads(version, expected):
    base = f'https://github.com/{REPOSITORY}/releases/download/server-v{version}/'
    for name, value in expected.items():
        with urllib.request.urlopen(base+name, timeout=120) as response:
            if hashlib.file_digest(response, 'sha256').hexdigest() != value:
                raise ValueError('Descarga pública incorrecta: '+name)


def publish():
    version = (ROOT/'VERSION').read_text().strip()
    package = ROOT/'yunohost'
    validate_package(package, version)
    payload = package/'payload'
    expected = {name: digest(payload/name) for name in NAMES}
    tag = 'server-v'+version
    # La consulta por etiqueta encuentra primero una release publicada. Los
    # borradores de intentos fallidos solo se consideran cuando no existe esa.
    query = subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/releases/tags/{tag}'],
                           capture_output=True, text=True)
    if query.returncode == 0:
        release = json.loads(query.stdout)
    else:
        if 'HTTP 404' not in query.stderr:
            raise RuntimeError('No se pudo consultar la release pública')
        drafts = [item for item in api('releases?per_page=100')
                  if item['tag_name'] == tag and item['draft']]
        if len(drafts) > 1:
            raise ValueError('Hay varios borradores de la versión; se requiere revisión')
        if drafts:
            release = drafts[0]
        else:
            head = api('git/ref/heads/main')['object']['sha']
            # La lista de releases puede tardar en reflejar una creación. La
            # respuesta del POST identifica el borrador sin depender de esa caché.
            release = json.loads(gh('api', f'repos/{REPOSITORY}/releases', '--method', 'POST',
                                    '-f', 'tag_name='+tag, '-f', 'target_commitish='+head,
                                    '-F', 'draft=true', '-f', 'name=Motor '+version,
                                    '-f', 'body=Motor Linux amd64/arm64. source.tar.gz contiene '
                                    'los fuentes completos correspondientes, dependencias y '
                                    'licencias. El paquete comprueba SHA-256.'))
            if release.get('tag_name') != tag or release.get('draft') is not True or not release.get('id'):
                raise ValueError('La respuesta de creación no identifica el borrador esperado')
    existing = {item['name']: item for item in release['assets']}
    if set(existing)-set(expected):
        raise ValueError('La release contiene recursos no esperados')
    for name, value in expected.items():
        if name in existing:
            if existing[name].get('digest') != 'sha256:'+value:
                raise ValueError('No se reemplaza un recurso publicado diferente: '+name)
        elif release['draft']:
            gh('release', 'upload', tag, str(payload/name), '--repo', REPOSITORY)
        else:
            raise ValueError('La release publicada está incompleta: '+name)
    if release['draft']:
        gh('release', 'edit', tag, '--repo', REPOSITORY, '--draft=false')
    published = api('releases/tags/'+tag)
    if published['draft'] or published['prerelease']:
        raise ValueError('La release aún no está publicada como estable')
    verify_downloads(version, expected)
    print('Tres recursos públicos de GitHub verificados por SHA-256.')


if __name__ == '__main__':
    publish()
