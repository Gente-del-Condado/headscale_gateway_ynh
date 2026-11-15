#!/usr/bin/env python3
"""Prepara una distribución individual de HA desde archivos confirmados en Git."""
import argparse
import io
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments])


def prepare(source, destination, domain, readme):
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('Se necesitan clones separados')
    if Path(domain).name != domain or not domain.replace('_', '').isalnum():
        raise ValueError('Dominio de integración no válido')
    if Path(readme).is_absolute() or '..' in Path(readme).parts:
        raise ValueError('README fuera del proyecto')
    if Path(git(destination, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != destination:
        raise ValueError('El destino no es la raíz de un clon Git')
    tracked = set(git(source, 'ls-tree', '-r', '--name-only', '-z', 'HEAD').decode().split('\0'))
    component = 'custom_components/'+domain
    for required in (component+'/manifest.json', readme, 'hacs.json'):
        if required not in tracked:
            raise ValueError('Archivo requerido sin confirmar: '+required)
    selected = [component, readme, 'hacs.json']
    selected += [name for name in ('LICENSE', 'NOTICE') if name in tracked]
    icons = {}
    for name in ('icon.png', 'logo.png'):
        options = (component+'/brand/'+name, 'packaging/homeassistant/'+name, 'addons/'+domain+'/'+name)
        for candidate in options:
            if candidate in tracked:
                icons[name] = candidate
                selected.append(candidate)
                break
    raw = git(source, 'archive', '--format=tar', 'HEAD', '--', *selected)
    with tempfile.TemporaryDirectory(prefix='ha-distribution-') as temporary:
        stage = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            members = archive.getmembers()
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise ValueError('Ruta o enlace no publicable')
            for member in members:
                path = stage/member.name
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as incoming, path.open('wb') as output:
                        shutil.copyfileobj(incoming, output)
        if not (stage/component/'manifest.json').is_file():
            raise ValueError('Falta el manifiesto de la integración')
        for required in (readme, 'hacs.json', *icons.values()):
            if not (stage/required).is_file():
                raise ValueError('Falta un archivo requerido para publicar: '+required)
        managed = [component, 'README.md', 'hacs.json', *icons]
        managed += [name for name in ('LICENSE', 'NOTICE') if (stage/name).is_file()]
        if (destination/'custom_components').is_symlink():
            raise ValueError('custom_components no puede ser un enlace')
        for name in managed:
            if (destination/name).is_symlink():
                raise ValueError('El destino no puede contener enlaces gestionados')
        target = destination/component
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(exist_ok=True)
        shutil.copytree(stage/component, target)
        shutil.copyfile(stage/readme, destination/'README.md')
        shutil.copyfile(stage/'hacs.json', destination/'hacs.json')
        for name in ('LICENSE', 'NOTICE'):
            if (stage/name).is_file():
                shutil.copyfile(stage/name, destination/name)
        for name, original in icons.items():
            shutil.copyfile(stage/original, destination/name)
    print('Distribución preparada; otros archivos y workflows se conservan.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--readme', required=True)
    arguments = parser.parse_args()
    prepare(ROOT, arguments.destination, arguments.domain, arguments.readme)
