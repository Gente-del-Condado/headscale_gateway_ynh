#!/usr/bin/env python3
"""Prepara instaladores y fuentes en un runner público, antes de publicarlos."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def run(arguments, root):
    subprocess.run([str(argument) for argument in arguments], cwd=root, check=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def zip_tree(destination, root, prefix=''):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                archive.write(path, prefix + path.relative_to(root).as_posix())


def build(root, output, android):
    if os.environ.get('GITHUB_REPOSITORY') != 'Gente-del-Condado/headscale_gateway_releases':
        raise ValueError('La compilación completa solo se ejecuta en el runner público autorizado')
    if output.exists() and any(output.iterdir()):
        raise ValueError('El directorio de entrega debe estar vacío')
    output.mkdir(parents=True, exist_ok=True)
    version = (root / 'VERSION').read_text().strip()
    sys.path.insert(0, str(root / 'tools'))
    from package_release import runtime_archives, write_archive
    from prepare_public_release import detach_sources
    from package_linux import build as build_linux
    from prepare_flatpak import prepare as prepare_flatpak
    from publish_public_sources import snapshot
    from desktop_sources import gateway_files

    # Solo incorporar Android después de comprobar todas las sumas de su constructor.
    expected = {}
    for line in (android / 'SHA256SUMS').read_text().splitlines():
        value, name = line.split(maxsplit=1)
        if Path(name).name != name or digest(android / name) != value:
            raise ValueError('Los resultados Android no coinciden con sus sumas')
        expected[name] = value
    if not {'headscale-gateway-release.apk', 'headscale-gateway-fdroid-unsigned.apk', 'headscale-gateway-play.aab', 'ANDROID-VALIDATION.json'} <= expected.keys():
        raise ValueError('Falta un canal Android verificado')
    for name in expected:
        shutil.move(android / name, output / name)
    run([sys.executable, 'tools/build_release.py'], root)
    runtime_archives(output, server_only=True)
    for architecture, directory in [('amd64', 'bin/linux'), ('arm64', 'bin/linux-arm64')]:
        for kind in ['deb', 'rpm']:
            build_linux(output, root / directory / 'headscale-gateway', root / directory / 'hgw-ca-helper', architecture, kind)
    run([sys.executable, 'tools/test_native_packages.py', output], root)

    run(['npm', 'ci', '--ignore-scripts', '--no-audit'], root / 'src/desktop')
    for platform, folder, name in [
        ('linux', 'bin/linux/Gateway-Tray', 'gateway-tray-linux-x64.tar.gz'),
        ('win32', 'bin/Gateway-Tray', 'gateway-tray-windows-x64.zip'),
    ]:
        run(['node', 'src/desktop/pack.cjs', platform], root)
        runtime = root / folder
        detach_sources(runtime, platform, output, f'https://github.com/Gente-del-Condado/headscale_gateway_releases/releases/download/v{version}/')
        pairs = [(path, 'Gateway-Tray/' + path.relative_to(runtime).as_posix()) for path in sorted(runtime.rglob('*')) if path.is_file()]
        write_archive(output / name, pairs, windows=platform == 'win32')
        shutil.rmtree(runtime)
    for folder in output.glob('*.parts'):
        for part in folder.glob('*.part-*'):
            shutil.move(part, output / part.name)
        shutil.rmtree(folder)

    for platform, tree, prefix in [('homeassistant', root / 'addons/headscale_gateway', 'homeassistant/headscale_gateway/'), ('yunohost', root / 'yunohost', 'yunohost/')]:
        zip_tree(output / f'headscale-gateway-{platform}-{version}.zip', tree, prefix)
    with zipfile.ZipFile(output / f'headscale-gateway-hacs-{version}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / 'custom_components/headscale_gateway').rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                archive.write(path, 'hacs/' + path.relative_to(root).as_posix())
        for source, name in [('packaging/hacs/README.md', 'README.md'), ('hacs.json', 'hacs.json'), ('LICENSE', 'LICENSE'), ('NOTICE', 'NOTICE')]:
            archive.write(root / source, 'hacs/' + name)
    with tempfile.TemporaryDirectory(prefix='hgw-public-source-') as temporary:
        tree = Path(temporary)
        snapshot(tree)
        zip_tree(output / f'headscale-gateway-fuentes-publicos-{version}.zip', tree, 'headscale-gateway/')
    shutil.copy2(root / 'yunohost/payload/source.tar.gz', output / f'headscale-gateway-go-sources-{version}.tar.gz')
    prepare_flatpak(output / 'flatpak-source')
    gateway_files(output, json.loads((root / 'packaging/desktop/electron-sources.lock.json').read_text()))
    (output / 'SHA256SUMS').write_text(''.join(digest(path) + '  ' + path.name + '\n' for path in sorted(output.iterdir()) if path.is_file()))
    print('INSTALADORES_PUBLICOS_PREPARADOS: ' + version, flush=True)


def flatpak(root, output):
    app = 'es.gentedelcondado.HeadscaleGateway'
    # La receta pública conserva las URL finales. Para probar antes de publicar,
    # otra copia usa los mismos binarios y sumas del payload ya validado.
    source = output / 'flatpak-source'
    local = output / 'flatpak-check-source'
    shutil.copytree(source, local)
    manifest = local / (app + '.json')
    data = json.loads(manifest.read_text())
    for module in data['modules']:
        for item in module['sources']:
            if item.get('type') == 'file' and 'url' in item:
                path = root / 'yunohost/payload' / item['url'].rsplit('/', 1)[1]
                if digest(path) != item['sha256']:
                    raise ValueError('Flatpak usa un binario que no coincide con el manifiesto')
                del item['url']
                item['path'] = str(path)
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    run(['appstreamcli', 'validate', '--no-net', local / 'files' / (app + '.metainfo.xml')], root)
    run(['flatpak-builder', '--user', '--install-deps-from=flathub', '--assumeyes', '--force-clean', '--repo=' + str(output / 'flatpak-repo'), output / 'flatpak-build', manifest], root)
    version = (root / 'VERSION').read_text().strip()
    bundle = output / f'headscale-gateway-{version}-x86_64.flatpak'
    run(['flatpak', 'build-bundle', output / 'flatpak-repo', bundle, app, '--runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo'], root)
    run(['flatpak', 'install', '--user', '--assumeyes', bundle], root)
    run(['flatpak', 'run', app, '--help'], root)
    for folder in [local, output / 'flatpak-build', output / 'flatpak-repo']:
        shutil.rmtree(folder)
    print('FLATPAK_INSTALADO_Y_COMPROBADO', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--android', type=Path)
    parser.add_argument('--flatpak-only', action='store_true')
    arguments = parser.parse_args()
    root, output = arguments.source.resolve(), arguments.output.resolve()
    if arguments.flatpak_only:
        flatpak(root, output)
    elif arguments.android:
        build(root, output, arguments.android.resolve())
    else:
        parser.error('Indica --android o --flatpak-only')
