#!/usr/bin/env python3
"""Publica resultados comprobados en seis destinos; nunca escribe en Forgejo."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

OWNER = 'Gente-del-Condado'
GENERAL = OWNER + '/headscale_gateway_releases'


def run(arguments, root):
    subprocess.run([str(item) for item in arguments], cwd=root, check=True)


def commit_and_push(clone, version, branch='main'):
    run(['git', 'config', 'user.name', 'github-actions[bot]'], clone)
    run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], clone)
    run(['git', 'add', '--all'], clone)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=clone).returncode
    if changed == 0:
        return
    if changed != 1:
        raise ValueError('No se pudo revisar el contenido preparado')
    run(['git', 'commit', '-m', 'Publicar Headscale Gateway ' + version], clone)
    # Otras aplicaciones pueden publicar simultáneamente en las tiendas.
    # Rebasar conserva sus cambios; un conflicto se detiene sin forzar la rama.
    for attempt in range(3):
        result = subprocess.run(['git', 'push', 'origin', 'HEAD:' + branch], cwd=clone)
        if result.returncode == 0:
            return
        if attempt < 2:
            run(['git', 'pull', '--rebase', 'origin', branch], clone)
    raise ValueError('No se pudo actualizar el destino sin forzar referencias')


def synchronize_controller(repository, source, version):
    """Solo actualiza metadatos; preserva el controlador que ejecuta la publicación."""
    if repository != GENERAL:
        raise ValueError('Este sincronizador solo administra el repositorio de descargas')
    allowed = {'README.md', 'LICENSE', 'NOTICE', 'icon.png'}
    if {path.name for path in source.iterdir()} != allowed:
        raise ValueError('El árbol de metadatos contiene archivos no autorizados')
    with tempfile.TemporaryDirectory(prefix='hgw-controller-metadata-') as temporary:
        clone = Path(temporary) / 'repository'
        run(['git', 'clone', '--depth=1', 'https://github.com/' + repository + '.git', clone], source)
        for name in allowed:
            shutil.copy2(source / name, clone / name)
        commit_and_push(clone, version)


def publish(root, output, source_sha):
    if os.environ.get('GITHUB_REPOSITORY') != GENERAL:
        raise ValueError('Solo publica el controlador autorizado')
    sys.path.insert(0, str(root / 'tools'))
    import publish_public_release as public
    import desktop_sources
    from forgejo_source import forgejo_json, validate_release
    version = (root / 'VERSION').read_text().strip()
    release = forgejo_json('/releases/tags/v' + version)
    validate_release(release)
    if forgejo_json('/tags/v' + version)['commit']['sha'] != source_sha:
        raise ValueError('La etiqueta ha cambiado desde las pruebas')
    # Los instaladores nuevos solo se publican después de comprobar sus fuentes.
    desktop_sources.publish(output / 'desktop-sources')
    run(['gh', 'auth', 'setup-git'], root)
    # Los tres recursos del paquete deben existir antes de actualizar su main.
    run([sys.executable, 'tools/publish_yunohost_assets.py'], root)
    with tempfile.TemporaryDirectory(prefix='hgw-destinations-') as temporary:
        base = Path(temporary)
        def clone(name, suffix='', branch='main'):
            destination = base / (name + suffix)
            run(['git', 'clone', '--depth=1', '--branch', branch, 'https://github.com/' + OWNER + '/' + name + '.git', destination], root)
            return destination
        ynh = clone('headscale_gateway_ynh')
        run([sys.executable, 'tools/publish_yunohost_repo.py', ynh], root)
        commit_and_push(ynh, version)
        run([sys.executable, 'tools/publish_public_sources.py', '--publish', ynh, '--tag'], root)
        ha = clone('headscale_gateway_ha')
        run([sys.executable, 'tools/publish_ha_repository.py', ha, '--domain', 'headscale_gateway', '--readme', 'packaging/hacs/README.md'], root)
        commit_and_push(ha, version)
        apps = clone('Mis_app_ha', branch='build-source')
        run(['bash', 'tools/publish_homeassistant_store.sh', apps], root)
        commit_and_push(apps, version, 'build-source')
        # No marcar completa la entrega hasta que la tienda anuncie la imagen
        # probada de este árbol. No hay credenciales de GHCR en este publicador.
        expected_tree = subprocess.check_output(['git', 'rev-parse', 'HEAD:addons/headscale_gateway'], cwd=root, text=True).strip()
        deadline = time.monotonic() + 1800
        while True:
            check = subprocess.run(['gh', 'api', 'repos/' + OWNER + '/Mis_app_ha/contents/.images/headscale_gateway.json?ref=main',
                                    '-H', 'Accept: application/vnd.github.raw+json'], capture_output=True, text=True)
            if check.returncode == 0:
                record = json.loads(check.stdout)
                if record.get('tree') == expected_tree and record.get('version') == version:
                    break
            if time.monotonic() >= deadline:
                raise ValueError('La imagen Home Assistant aún no está verificada y publicada; no se marca completa la entrega')
            time.sleep(20)
        components = clone('Mis_componente_ha')
        destination = components / 'headscale_gateway'
        if destination.is_symlink():
            raise ValueError('La integración de destino no puede ser un enlace')
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(root / 'custom_components/headscale_gateway', destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ['LICENSE', 'NOTICE']:
            shutil.copy2(root / name, destination / name)
        commit_and_push(components, version)
        for name in ['headscale_gateway_ynh', 'headscale_gateway_ha']:
            manual = clone(name, '-manual', 'gh-pages')
            run([sys.executable, 'tools/publish_manual.py', root / 'builds/manual', manual], root)
            commit_and_push(manual, version, 'gh-pages')

    # El publicador original conoce las sumas y las cuatro particiones. Su
    # sincronización general se sustituye para preservar workflows y automation/.
    original = public.synchronize_public_tree
    def synchronize(repository, source):
        if repository == GENERAL:
            synchronize_controller(repository, source, version)
        else:
            original(repository, source)
    public.synchronize_public_tree = synchronize
    previous = sys.argv
    try:
        sys.argv = ['publish_public_release.py', str(output), str(output)]
        public.main()
    finally:
        sys.argv = previous
    # Este recibo solo se escribe después de verificar las descargas anónimas
    # y completar tiendas, fuentes, paquetes y ramas del manual.
    metadata = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + GENERAL + '/releases/tags/v' + version], text=True))
    body = (metadata.get('body') or '') + '\n\nFuentes Forgejo: `' + source_sha + '`. Control público: `' + os.environ['GITHUB_SHA'] + '`.\n<!-- hgw-complete:' + source_sha + ' -->\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as notes:
        notes.write(body)
        notes.flush()
        run(['gh', 'release', 'edit', 'v' + version, '--repo', GENERAL, '--notes-file', notes.name], root)
    print('PUBLICACION_COMPLETA_OK: paquetes, tiendas, manuales y descargas verificadas', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    arguments = parser.parse_args()
    publish(arguments.source.resolve(), arguments.output.resolve(), arguments.sha)
