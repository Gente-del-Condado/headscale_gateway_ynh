#!/usr/bin/env python3
"""Fuentes de terceros reutilizables, identificados por su lock completo."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

from split_release import split

REPOSITORY = 'Gente-del-Condado/headscale_gateway_releases'
WEB = 'https://github.com/' + REPOSITORY
CHUNK = 1500000000
MAX_SINGLE = 2000000000


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(lock):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', lock.get('electron_version', '')):
        raise ValueError('Versión de Electron no válida')
    names = set()
    for record in lock['sources']:
        name = record['name']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) or name in names:
            raise ValueError('Nombre de fuente no válido o repetido')
        if not re.fullmatch('[0-9a-f]{64}', record['sha256']) or type(record['size']) is not int or record['size'] <= 0:
            raise ValueError('Fuente sin tamaño y suma válidos')
        names.add(name)
    if not names:
        raise ValueError('El lock debe contener fuentes')
    value = hashlib.sha256(json.dumps({'format': 1, 'chunk_bytes': CHUNK, 'lock': lock}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return 'desktop-sources-electron-' + lock['electron_version'] + '-' + value[:16]


def references(lock):
    base = WEB + '/releases/download/' + identity(lock) + '/'
    records = []
    for record in lock['sources']:
        entry = dict(record)
        if record['size'] > MAX_SINGLE:
            entry.update(download_parts=[base + record['name'] + '.part-' + str(i + 1).zfill(2)
                                         for i in range(math.ceil(record['size'] / CHUNK))],
                         parts_manifest=base + record['name'] + '.parts.json')
        else:
            entry['download'] = base + record['name']
        records.append(entry)
    return {'format': 1, 'tag': identity(lock), 'release': WEB + '/releases/tag/' + identity(lock),
            'lock': lock, 'sources': records}


def gateway_files(folder, lock):
    """Impide volver a mezclar fuentes de terceros con los adjuntos de Gateway."""
    identity(lock)
    names = {record['name'] for record in lock['sources']}
    selected = []
    for path in sorted(Path(folder).iterdir()):
        if path.is_symlink():
            raise ValueError('No se publican enlaces desde la entrega')
        if not path.is_file():
            continue
        if path.name == 'desktop-sources' or any(
                path.name == name or path.name == name + '.parts.json' or
                path.name.startswith(name + '.part-') for name in names):
            raise ValueError('Fuentes de terceros fuera de su release reutilizable: ' + path.name)
        if path.name != 'SHA256SUMS':
            selected.append(path)
    return selected


def prepare(sources, lock, destination):
    """No cambia un conjunto existente ni acepta fuentes de otra revisión."""
    document = references(lock)
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError('El destino de fuentes no puede ser un enlace')
    if destination.exists() and any(destination.iterdir()):
        previous = json.loads((destination / 'DESKTOP-SOURCES.json').read_text())
        if any(previous.get(key) != value for key, value in document.items()):
            raise ValueError('El conjunto de fuentes existente corresponde a otro lock')
        verify(destination)
        return previous
    destination.mkdir(parents=True, exist_ok=True)
    for record in lock['sources']:
        source = Path(sources) / record['name']
        if source.is_symlink() or source.stat().st_size != record['size'] or digest(source) != record['sha256']:
            raise ValueError('Fuente no correspondiente al lock: ' + record['name'])
    # Preparar en otra carpeta evita reutilizar una separación interrumpida.
    with tempfile.TemporaryDirectory(prefix='desktop-sources-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        for record in lock['sources']:
            source = Path(sources) / record['name']
            if record['size'] > MAX_SINGLE:
                fragments = stage / 'parts'
                split(source, fragments, record['name'], CHUNK)
                for part in fragments.glob('*.part-*'):
                    shutil.move(part, stage / part.name)
                shutil.move(fragments / 'parts.json', stage / (record['name'] + '.parts.json'))
                fragments.rmdir()
            else:
                shutil.copy2(source, stage / source.name)
        (stage / 'RECONSTRUIR.md').write_text(
            '# Fuentes reutilizables de Electron y sus dependencias\n\n'
            'Este conjunto no es un instalador. DESKTOP-SOURCES.json fija las revisiones,\n'
            'procedencia HTTPS y sumas de Electron, Chromium (con FFmpeg), Node y NAN.\n'
            'Electron incluye sus parches, DEPS, configuración GN y scripts.\n'
            'Conserva los LICENSE de los archivos y los avisos originales de cada runtime.\n'
            'No se relicencian los componentes con la licencia de Gateway.\n\n'
            'Comprueba SHA256SUMS. Si Chromium tiene partes, únelas en orden y comprueba\n'
            'también el SHA-256 del archivo completo de su .parts.json antes de extraer.\n'
            'Usa las instrucciones upstream de la revisión Electron indicada en el lock:\n'
            'https://www.electronjs.org/docs/latest/development/build-instructions-gn\n'
            'aplicando sus parches y DEPS exactos, no las revisiones actuales.\n'
            'Gateway-Tray conserva en legal/application-source/ las instrucciones de\n'
            'packaging/desktop/README.md y el código propio para esa entrega.\n'
            'No se afirma una reconstrucción binaria idéntica del runtime oficial.\n\n'
            'FFmpeg mantiene LGPL-2.1-or-later y sus avisos. Se puede sustituir la\n'
            'biblioteca dinámica por otra compatible; se permite depurar sus cambios.\n')
        document['files'] = {p.name: digest(p) for p in sorted(stage.iterdir())}
        (stage / 'DESKTOP-SOURCES.json').write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')
        (stage / 'SHA256SUMS').write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in sorted(stage.iterdir())))
        for path in stage.iterdir():
            shutil.move(path, destination / path.name)
    verify(destination)
    return document


def verify(folder):
    folder = Path(folder)
    document = json.loads((folder / 'DESKTOP-SOURCES.json').read_text())
    expected = references(document['lock'])
    if any(document.get(key) != value for key, value in expected.items()):
        raise ValueError('Índice de fuentes incompatible con el lock')
    sums = {}
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        value, name = line.split(maxsplit=1)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) or name in sums:
            raise ValueError('Manifiesto de fuentes no válido')
        sums[name] = value
    files = {p.name: digest(p) for p in folder.iterdir() if p.is_file() and not p.is_symlink() and p.name != 'SHA256SUMS'}
    if sums != files or set(p.name for p in folder.iterdir()) != set(sums) | {'SHA256SUMS'}:
        raise ValueError('Fuentes incompletos, alterados o archivos ajenos')
    for record in document['lock']['sources']:
        if record['size'] <= MAX_SINGLE:
            if files.get(record['name']) != record['sha256'] or (folder / record['name']).stat().st_size != record['size']:
                raise ValueError('Archivo de fuentes ajeno al lock')
        else:
            parts = json.loads((folder / (record['name'] + '.parts.json')).read_text())
            if parts['archive'] != record['name'] or parts['sha256'] != record['sha256'] or sum(p['bytes'] for p in parts['parts']) != record['size']:
                raise ValueError('Fragmentos ajenos al lock')
            combined = hashlib.sha256()
            for index, part in enumerate(parts['parts'], 1):
                if part['name'] != record['name'] + '.part-' + str(index).zfill(2) or files.get(part['name']) != part['sha256']:
                    raise ValueError('Orden o suma de fragmentos no válido')
                with (folder / part['name']).open('rb') as stream:
                    while block := stream.read(1024 * 1024):
                        combined.update(block)
            if combined.hexdigest() != record['sha256']:
                raise ValueError('La reconstrucción difiere del lock')
    if document.get('files') != {name: value for name, value in files.items() if name != 'DESKTOP-SOURCES.json'}:
        raise ValueError('El índice no coincide con los archivos de fuentes')
    return document


def publish(folder):
    from publish_public_release import publish_files
    folder = Path(folder)
    document = verify(folder)
    # No se convierte una entrega de dependencias en «Latest» de la aplicación.
    # publish_files compara SHA-256 y nunca reemplaza adjuntos existentes.
    result = publish_files(REPOSITORY, document['tag'], sorted(folder.iterdir()),
                           'Fuentes reutilizables de Electron ' + document['lock']['electron_version'] +
                           ' y sus dependencias. No son instaladores de Gateway.\n\n'
                           'Conservan licencias originales, FFmpeg, parches y referencias exactas. '
                           'Ver DESKTOP-SOURCES.json, RECONSTRUIR.md y SHA256SUMS.\n', latest=False, reuse=True)
    print('FUENTES_ESCRITORIO_REUTILIZABLES_OK: ' + document['release'], flush=True)
    return result


def seed(lock, release, destination):
    """Copia archivos públicos de una entrega anterior sin editarla ni borrarla."""
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', release):
        raise ValueError('Release de origen no válida')
    metadata = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + REPOSITORY + '/releases/tags/' + release], text=True))
    if metadata['draft'] or metadata['prerelease']:
        raise ValueError('El origen debe ser una release publicada')
    assets = {a['name']: a for a in metadata['assets']}
    identity(lock)
    def download(name, stream, checksum, size):
        asset = assets[name]
        url = WEB + '/releases/download/' + release + '/' + name
        if asset['size'] != size or asset.get('digest') != 'sha256:' + checksum:
            raise ValueError('El adjunto de origen no corresponde a la suma esperada')
        value, total = hashlib.sha256(), 0
        with urllib.request.urlopen(url, timeout=180) as response:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > size:
                    raise ValueError('Descarga de fuentes demasiado grande')
                value.update(block)
                stream.write(block)
        if total != size or value.hexdigest() != checksum:
            raise ValueError('Descarga pública de fuentes alterada')
    with tempfile.TemporaryDirectory(prefix='hgw-source-seed-') as temporary:
        cache = Path(temporary)
        for record in lock['sources']:
            with (cache / record['name']).open('wb') as stream:
                if record['name'] not in assets and record['name'] + '.parts.json' not in assets:
                    # Una futura revisión de Electron puede no existir en la 1.4.16.
                    # Descargar su fuente upstream exige la suma fijada en el lock.
                    from urllib.parse import urlsplit
                    origin = urlsplit(record['url'])
                    if origin.scheme != 'https' or origin.hostname not in {'commondatastorage.googleapis.com', 'codeload.github.com', 'nodejs.org'} or origin.username or origin.password or origin.port:
                        raise ValueError('Origen upstream no autorizado')
                    with urllib.request.urlopen(record['url'], timeout=180) as response:
                        total = 0
                        while block := response.read(1024 * 1024):
                            total += len(block)
                            if total > record['size']:
                                raise ValueError('Fuente upstream demasiado grande')
                            stream.write(block)
                    # prepare vuelve a comprobar tamaño y SHA-256 antes de separar.
                elif record['size'] <= MAX_SINGLE:
                    download(record['name'], stream, record['sha256'], record['size'])
                else:
                    import io
                    name = record['name'] + '.parts.json'
                    manifest = io.BytesIO()
                    download(name, manifest, assets[name]['digest'].removeprefix('sha256:'), assets[name]['size'])
                    parts = json.loads(manifest.getvalue())
                    if parts['archive'] != record['name'] or parts['sha256'] != record['sha256']:
                        raise ValueError('Las partes no pertenecen a los fuentes fijados')
                    if sum(p['bytes'] for p in parts['parts']) != record['size']:
                        raise ValueError('Partes incompletas')
                    for index, part in enumerate(parts['parts'], 1):
                        if part['name'] != record['name'] + '.part-' + str(index).zfill(2):
                            raise ValueError('Orden o nombre de fragmento inválido')
                        download(part['name'], stream, part['sha256'], part['bytes'])
        return prepare(cache, lock, destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed-from', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    seed(json.loads(args.lock.read_text()), args.seed_from, args.output)
    if args.publish:
        publish(args.output)
