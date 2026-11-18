#!/usr/bin/env python3
"""Construye la tienda desde fuentes preparados; publica solo imágenes verificadas."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

REPOSITORY = 'Gente-del-Condado/Mis_app_ha'
SOURCE_BRANCH = 'build-source'
APPS = ('headscale_gateway', 'jacksignal_installer', 'pivigia', 'private_git_manager')
ORIGINS = {'headscale_gateway': 'headscale_gateway', 'jacksignal_installer': 'jacksignal',
           'pivigia': 'pivigia', 'private_git_manager': 'HA-Private-Git-Manager'}
PLATFORMS = {'amd64': ('amd64', 'ubuntu-24.04'), 'aarch64': ('arm64', 'ubuntu-24.04-arm')}
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] if HERE.name == 'ha-images' else HERE


def run(*args, capture=False, root=None):
    return subprocess.run([str(a) for a in args], cwd=root, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def git(*args, capture=True):
    return run('git', *args, capture=capture)


def image_name(app):
    if app not in APPS:
        raise ValueError('Aplicación fuera de la tienda autorizada')
    return 'ghcr.io/gente-del-condado/ha-' + app.replace('_', '-')


def config(app, sha):
    document = yaml.safe_load(git('show', f'{sha}:{app}/config.yaml'))
    if (document.get('slug') != app or set(document.get('arch', [])) != set(PLATFORMS)
            or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', str(document.get('version', '')))):
        raise ValueError('Manifiesto de aplicación no compatible con ambas arquitecturas')
    return document


def refresh():
    git('fetch', '--no-tags', 'origin', '+refs/heads/main:refs/remotes/origin/main',
        '+refs/heads/build-source:refs/remotes/origin/build-source', capture=False)


def select():
    if os.environ.get('GITHUB_REPOSITORY', REPOSITORY) != REPOSITORY:
        raise ValueError('Repositorio de publicación no autorizado')
    refresh()
    sha = git('rev-parse', 'origin/' + SOURCE_BRANCH).strip()
    entries = git('ls-tree', '--name-only', sha).splitlines()
    for entry in entries:
        if entry not in APPS:
            check = subprocess.run(['git', 'cat-file', '-e', f'{sha}:{entry}/config.yaml'], capture_output=True)
            if check.returncode == 0:
                raise ValueError('Aplicación nueva sin pruebas de contenedor: ' + entry)
    apps, builds = [], []
    for app in APPS:
        document = config(app, sha)
        version = str(document['version'])
        tree = git('rev-parse', f'{sha}:{app}').strip()
        record = subprocess.run(['git', 'show', f'origin/main:.images/{app}.json'], capture_output=True, text=True)
        if record.returncode == 0:
            previous = json.loads(record.stdout)
            if previous['tree'] == tree:
                continue
            if previous['version'] == version:
                raise ValueError('Incrementa la versión antes de cambiar una imagen publicada: ' + app)
            if tuple(map(int, version.split('.'))) < tuple(map(int, previous['version'].split('.'))):
                raise ValueError('No se retrocede a una versión anterior: ' + app)
        value = {'app': app, 'version': version, 'tree': tree, 'sha': sha, 'image': image_name(app)}
        apps.append(value)
        for arch, (docker_arch, runner) in PLATFORMS.items():
            builds.append(dict(value, arch=arch, platform='linux/' + docker_arch, runner=runner))
    return {'include': builds}, apps, sha


def candidate(item, arch):
    return item['image'] + ':candidate-' + item['version'] + '-' + arch + '-' + item['tree'][:16]


def inspect(reference):
    result = subprocess.run(['docker', 'buildx', 'imagetools', 'inspect', '--raw', reference], capture_output=True, text=True)
    if result.returncode:
        if any(s in result.stderr.lower() for s in ('not found', 'manifest unknown', 'name unknown')):
            return None
        raise ValueError('No se pudo consultar la imagen; no se reemplaza su etiqueta')
    return json.loads(result.stdout)


def registry(reference):
    image, tag = reference.rsplit(':', 1)
    name = image.removeprefix('ghcr.io/')
    if image not in [image_name(app) for app in APPS] or not re.fullmatch(r'[a-zA-Z0-9._-]+', tag):
        raise ValueError('Referencia pública de imagen no válida')
    query = urllib.parse.urlencode({'scope': 'repository:' + name + ':pull', 'service': 'ghcr.io'})
    # Solicitar acceso anónimo sin usar Docker config, GITHUB_TOKEN o cookies.
    with urllib.request.urlopen('https://ghcr.io/token?' + query, timeout=30) as response:
        token = json.load(response)['token']
    request = urllib.request.Request('https://ghcr.io/v2/' + name + '/manifests/' + tag,
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(1024 * 1024)
        digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
        if response.headers.get('Docker-Content-Digest') != digest:
            raise ValueError('El manifiesto descargado no coincide con su digest')
        return json.loads(raw), digest


def validate_index(document):
    platforms = [(m.get('platform', {}).get('os'), m.get('platform', {}).get('architecture'))
                 for m in document.get('manifests', [])]
    if sorted(platforms) != [('linux', 'amd64'), ('linux', 'arm64')]:
        raise ValueError('La imagen no contiene exactamente amd64 y arm64')


def build(app, arch, sha):
    if app not in APPS or arch not in PLATFORMS or not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Trabajo de compilación no válido')
    if git('rev-parse', 'HEAD').strip() != sha:
        raise ValueError('El checkout no corresponde al commit aprobado')
    document = config(app, sha)
    item = {'app': app, 'image': image_name(app), 'version': str(document['version']),
            'tree': git('rev-parse', f'{sha}:{app}').strip()}
    reference = candidate(item, arch)
    existing = inspect(reference)
    if existing:
        run('docker', 'pull', reference)
    else:
        run('docker', 'build', '--platform', 'linux/' + PLATFORMS[arch][0],
            '--build-arg', 'BUILD_ARCH=' + arch, '--build-arg', 'BUILD_VERSION=' + item['version'],
            '--label', 'io.hass.type=app', '--label', 'io.hass.arch=' + arch,
            '--label', 'io.hass.version=' + item['version'], '--label', 'org.opencontainers.image.source=https://github.com/' + REPOSITORY,
            '--label', 'org.opencontainers.image.revision=' + sha,
            '--label', 'es.gentedelcondado.source-tree=' + item['tree'], '-t', reference, app)
    metadata = json.loads(run('docker', 'image', 'inspect', reference, capture=True))[0]
    labels = metadata['Config'].get('Labels', {})
    if (metadata['Architecture'] != PLATFORMS[arch][0] or labels.get('io.hass.arch') != arch
            or labels.get('io.hass.version') != item['version']
            or labels.get('es.gentedelcondado.source-tree') != item['tree']):
        raise ValueError('La imagen no corresponde al origen o a su plataforma')
    run('python3', HERE / 'smoke.py', '--app', app, '--image', reference, '--version', item['version'])
    if not existing:
        run('docker', 'push', reference)
    print('IMAGEN_NATIVA_PROBADA:', app, arch, item['version'], flush=True)


def publish(items):
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Solo publica la tienda autorizada')
    for item in items:
        app = item['app']
        if app not in APPS or item['image'] != image_name(app):
            raise ValueError('Destino de imagen no autorizado')
        reference = item['image'] + ':' + item['version']
        # No sobrescribir la etiqueta de una versión ya distribuida.
        document = inspect(reference)
        if document is None:
            run('docker', 'buildx', 'imagetools', 'create', '-t', reference,
                *[candidate(item, arch) for arch in PLATFORMS])
        else:
            validate_index(document)
            # La etiqueta estable solo puede proceder de estos candidatos inmutables.
            expected = []
            for arch in PLATFORMS:
                descriptor = json.loads(run('docker', 'buildx', 'imagetools', 'inspect', '--format', '{{json .Manifest}}', candidate(item, arch), capture=True))
                expected.append(descriptor['digest'])
            if sorted(m['digest'] for m in document['manifests']) != sorted(expected):
                raise ValueError('La etiqueta de versión ya apunta a imágenes distintas')
        # La primera publicación GHCR nace privada. Esperar su configuración pública
        # sin publicar un config.yaml que exija credenciales a Home Assistant.
        deadline = time.monotonic() + 900
        while True:
            try:
                public, digest = registry(reference)
                validate_index(public)
                break
            except (urllib.error.HTTPError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise ValueError('El paquete GHCR debe permitir descarga anónima antes de actualizar la tienda') from None
                print('ESPERANDO_VISIBILIDAD_PUBLICA:', item['image'], flush=True)
                time.sleep(20)
        item['digest'] = digest
        print('INDICE_PUBLICO_VERIFICADO:', reference, digest, flush=True)
    # Preparar todos los índices antes de editar main; un fallo conserva la tienda.
    for attempt in range(3):
        refresh()
        for item in items:
            if git('rev-parse', f'origin/{SOURCE_BRANCH}:{item["app"]}').strip() != item['tree']:
                raise ValueError('El origen cambió durante la compilación; se conserva la tienda')
        git('checkout', '-B', 'publish-images', 'origin/main', capture=False)
        for item in items:
            app = item['app']
            target = Path(app)
            if target.is_symlink():
                raise ValueError('Destino enlazado en la tienda')
            if target.exists():
                shutil.rmtree(target)
            target.mkdir()
            raw = subprocess.check_output(['git', 'archive', '--format=tar', f'origin/{SOURCE_BRANCH}:{app}'])
            import io, tarfile
            from pathlib import PurePosixPath
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                for member in archive:
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                        raise ValueError('Archivo no publicable en la aplicación')
                    destination = target.joinpath(*path.parts)
                    if member.isdir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.extractfile(member) as stream:
                            destination.write_bytes(stream.read())
                        destination.chmod(0o755 if member.mode & 0o111 else 0o644)
            path = target / 'config.yaml'
            text = path.read_text()
            text = re.sub(r'^image:.*\n?', '', text, flags=re.M)
            path.write_text(text.rstrip() + '\nimage: ' + item['image'] + '\n')
            record = Path('.images') / (app + '.json')
            record.parent.mkdir(exist_ok=True)
            record.write_text(json.dumps(dict(item, origin='https://gentedelcondado.es/forgejo/wolfbelmi88/' + ORIGINS[app]), indent=2) + '\n')
            git('add', '--', app, str(record), capture=False)
        if subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode == 0:
            return
        git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit', '-m', 'Publicar imágenes Home Assistant verificadas para amd64 y aarch64', capture=False)
        result = subprocess.run(['git', 'push', 'origin', 'HEAD:main'])
        if result.returncode == 0:
            print('TIENDA_CON_IMAGENES_PRECOMPILADAS_OK', flush=True)
            return
    raise ValueError('No se pudo actualizar main sin forzar referencias')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('plan')
    b = commands.add_parser('build')
    b.add_argument('--app', required=True)
    b.add_argument('--arch', required=True)
    b.add_argument('--sha', required=True)
    p = commands.add_parser('publish')
    p.add_argument('--items', required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        matrix, apps, sha = select()
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                stream.write('matrix=' + json.dumps(matrix) + '\n')
                stream.write('apps=' + json.dumps(apps) + '\n')
                stream.write('sha=' + sha + '\nchanged=' + str(bool(apps)).lower() + '\n')
        print(json.dumps({'matrix': matrix, 'apps': apps, 'sha': sha}))
    elif args.command == 'build':
        build(args.app, args.arch, args.sha)
    else:
        publish(json.loads(args.items))
