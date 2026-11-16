#!/usr/bin/env python3
"""Detecta estado privado y credenciales evidentes sin imprimir sus valores.

Revisa el índice y las fuentes locales, incluidas las ignoradas. Sin Git
recorre solo las carpetas de fuentes conocidas. Gitleaks y la revisión humana
complementan este control: no demuestra ausencia absoluta de secretos.
"""
from pathlib import Path
import re
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = {'src', 'android', 'tools', 'tests', 'docs', 'examples',
               'packaging', 'custom_components', 'addons', 'yunohost', '.github'}
CACHE = {'.git', 'node_modules', '__pycache__', '.gradle', '.kotlin', '.cxx', 'build', 'dist', '.cache'}
PRIVATE_SUFFIXES = {'.key', '.p12', '.pfx', '.jks', '.keystore', '.sqlite', '.sqlite3', '.sqlite-wal', '.sqlite-shm', '.hgw', '.hgwcfg', '.password'}
PRIVATE_NAMES = {'.env', 'credentials.json', 'signing.json', 'gateway.sqlite-wal', 'gateway.sqlite-shm', 'tailscaled.state'}
PATTERNS = {
    'clave privada PEM': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{100,}-----END'),
    'token GitHub': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{60,})\b'),
    'credencial Headscale': re.compile(rb'\bhskey-(?:api|auth)-[A-Za-z0-9_-]{20,}\b'),
    'ruta personal absoluta': re.compile(rb'/home/(?!yunohost\.(?:app|backup|multimedia)|[A-Z_]+/|(?:user|usuario|example|test|runner)/)[A-Za-z][A-Za-z0-9_.-]*/'),
}


def source_paths(root):
    # Incluye el índice aunque tenga archivos ignorados añadidos a la fuerza.
    # Revisa también fuentes ignoradas locales: .gitignore no es una auditoría.
    paths = set()
    if (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                                check=True, capture_output=True)
        paths.update(root / name.decode() for name in result.stdout.split(b'\0') if name)
    paths.update(p for p in root.iterdir() if p.is_file())
    for name in SOURCE_DIRS:
        folder = root / name
        if not folder.exists():
            continue
        if folder.is_symlink():
            paths.add(folder)
            continue
        for directory, folders, files in os.walk(folder):
            current = Path(directory)
            paths.update(current / child for child in folders if (current / child).is_symlink())
            folders[:] = [child for child in folders if child not in CACHE and not (current / child).is_symlink()]
            paths.update(current / name for name in files)
    return paths


def inspect(path):
    if path.is_symlink():
        return ['enlace simbólico en fuentes']
    if not path.exists():
        return []  # Una eliminación preparada aún puede figurar en el índice.
    if path.suffix.lower() in PRIVATE_SUFFIXES or path.name in PRIVATE_NAMES or path.name.startswith('.env.'):
        return ['archivo de estado o credenciales']
    # Los paquetes versionados contienen ELF y archivos comprimidos verificados
    # por sus manifiestos. Su revisión requiere exportar y auditar los fuentes.
    if path.suffix in {'.gz', '.png', '.jpg', '.jar', '.mo'}:
        return []
    with path.open('rb') as source:
        header = source.read(4096)
        if b'\0' in header:
            return []
        body = header + source.read()
    return [name for name, pattern in PATTERNS.items() if pattern.search(body)]


def check(root=ROOT):
    issues = []
    paths = source_paths(root)
    for path in sorted(paths):
        for reason in inspect(path):
            issues.append((path.relative_to(root).as_posix(), reason))
    if issues:
        raise ValueError('Revisar archivos antes de publicar:\n' + '\n'.join(name + ': ' + reason for name, reason in issues))
    print(f'OK: privacidad básica de {len(paths)} archivos; valores privados no mostrados')


if __name__ == '__main__':
    check()
