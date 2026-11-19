#!/usr/bin/env python3
"""Exporta únicamente el controlador público de la tienda; nunca claves o APK locales."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FILES = ('README.md', 'LICENSE', 'requirements.txt', 'store.json', 'repo-icon.png',
         'metadata/org.headscalegateway.android/en-US/images/icon.png',
         'automation/sync.py', 'automation/test_sync.py', '.github/workflows/publish.yml')


def prepare(destination):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('El destino debe estar vacío')
    for name in FILES:
        source = ROOT/'packaging/fdroid-store'/name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Fuente de tienda no válida: '+name)
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    (destination/'SOURCE_ORIGIN.json').write_text(json.dumps({
        'format':1,'repository':'https://gentedelcondado.es/forgejo/wolfbelmi88/headscale_gateway',
        'commit':commit,'path':'packaging/fdroid-store'},indent=2)+'\n')
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    print(prepare(parser.parse_args().destination))
