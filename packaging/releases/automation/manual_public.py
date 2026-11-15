#!/usr/bin/env python3
"""Actualiza la guía de una entrega completada sin modificar sus instaladores."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from publish_public import commit_and_push


def publish(root):
    if os.environ.get('GITHUB_REPOSITORY') != 'Gente-del-Condado/headscale_gateway_releases':
        raise ValueError('Controlador no autorizado')
    version = (root / 'VERSION').read_text().strip()
    subprocess.run(['gh', 'auth', 'setup-git'], check=True)
    with tempfile.TemporaryDirectory(prefix='hgw-current-manual-') as temporary:
        for name in ['headscale_gateway_ynh', 'headscale_gateway_ha']:
            destination = Path(temporary) / name
            subprocess.run(['git', 'clone', '--depth=1', '--branch', 'gh-pages', 'https://github.com/Gente-del-Condado/' + name + '.git', str(destination)], check=True)
            subprocess.run([sys.executable, str(root / 'tools/publish_manual.py'), str(root / 'builds/manual'), str(destination)], check=True)
            commit_and_push(destination, version, 'gh-pages')
    print('GUIAS_VIGENTES_PUBLICADAS: dos ramas gh-pages; instaladores intactos')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    publish(parser.parse_args().source.resolve())
