#!/usr/bin/env python3
"""Comprueba fuentes públicos reutilizables solo mediante lecturas, sin subir archivos."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from desktop_sources import WEB, REPOSITORY, references


def read(url):
    # No usa GH_TOKEN ni el helper de autenticación. Solo JSON y sumas pequeños.
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read(2 ** 20 + 1)
        if response.status != 200 or len(body) > 2 ** 20:
            raise ValueError('Respuesta pública fuera de los límites')
        return body


def check(lock, allow_missing=False):
    expected = references(lock)
    try:
        metadata = json.loads(read('https://api.github.com/repos/' + REPOSITORY + '/releases/tags/' + expected['tag']))
    except urllib.error.HTTPError as error:
        if error.code == 404 and allow_missing:
            return None
        raise
    if metadata['draft'] or metadata['prerelease'] or metadata['tag_name'] != expected['tag']:
        raise ValueError('La release de fuentes no está publicada o no corresponde al lock')
    assets = {item['name']: item for item in metadata['assets']}
    base = WEB + '/releases/download/' + expected['tag'] + '/'
    def verified(name):
        body = read(base + name)
        if assets[name].get('digest') != 'sha256:' + hashlib.sha256(body).hexdigest():
            raise ValueError('Índice público alterado: ' + name)
        return body
    index = json.loads(verified('DESKTOP-SOURCES.json'))
    if any(index.get(key) != value for key, value in expected.items()):
        raise ValueError('Los fuentes publicados pertenecen a otro lock')
    files = index['files']
    if 'RECONSTRUIR.md' not in files or set(assets) != set(files) | {'DESKTOP-SOURCES.json', 'SHA256SUMS'}:
        raise ValueError('La release reutilizable está incompleta')
    sums = {}
    for line in verified('SHA256SUMS').decode().splitlines():
        value, name = line.split(maxsplit=1)
        if name in sums:
            raise ValueError('Suma duplicada')
        sums[name] = value
    if set(sums) != set(assets) - {'SHA256SUMS'}:
        raise ValueError('Las sumas no cubren todos los archivos')
    for name, value in sums.items():
        if assets[name].get('digest') != 'sha256:' + value:
            raise ValueError('Un adjunto publicado difiere de sus sumas: ' + name)
    for name, value in files.items():
        if sums.get(name) != value:
            raise ValueError('El índice difiere de las sumas')
    for record in expected['sources']:
        if 'download' in record:
            if files.get(record['name']) != record['sha256'] or assets[record['name']]['size'] != record['size']:
                raise ValueError('Fuente publicada distinta del lock')
        else:
            parts = json.loads(verified(record['name'] + '.parts.json'))
            if parts['archive'] != record['name'] or parts['sha256'] != record['sha256']:
                raise ValueError('Fragmentos de otra revisión')
            if sum(item['bytes'] for item in parts['parts']) != record['size']:
                raise ValueError('Fragmentos incompletos')
            if [base + item['name'] for item in parts['parts']] != record['download_parts']:
                raise ValueError('Orden o nombre de fragmentos no válido')
            for item in parts['parts']:
                if files.get(item['name']) != item['sha256'] or assets[item['name']]['size'] != item['bytes']:
                    raise ValueError('Fragmento publicado alterado')
    return expected['release']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--allow-missing', action='store_true', help='Solo un 404 de la release permite preparar un conjunto nuevo')
    args = parser.parse_args()
    release = check(json.loads(args.lock.read_text()), args.allow_missing)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('exists=' + str(release is not None).lower() + '\n')
    print('FUENTES_EXISTENTES_VERIFICADOS_SIN_SUBIDAS: ' + release if release else 'Falta publicar un conjunto nuevo para este lock')
