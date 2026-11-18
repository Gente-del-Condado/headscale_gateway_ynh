#!/usr/bin/env python3
"""Retira releases antiguas de Gateway; conserva Git y todos los fuentes Electron."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

OWNER = 'Gente-del-Condado'
GENERAL = OWNER + '/headscale_gateway_releases'
GITHUB_REPOS = (GENERAL, OWNER + '/headscale_gateway_flatpak',
                OWNER + '/headscale_gateway_ynh', OWNER + '/headscale_gateway_ha')
FORGEJO_REPO = 'wolfbelmi88/headscale_gateway'
FORGEJO_API = 'http://127.0.0.1:6000/api/v1'
MARKER = re.compile(r'<!-- hgw-complete:([0-9a-f]{40}) -->')
VERSION = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class API:
    def __init__(self, forge='github', token=''):
        self.forge = forge
        local = os.environ.get('HGW_FORGEJO_API', FORGEJO_API)
        if forge == 'forgejo' and local not in (FORGEJO_API, 'http://127.0.0.1:6000/forgejo/api/v1'):
            raise ValueError('Solo se permite la API local de Forgejo')
        self.base = 'https://api.github.com' if forge == 'github' else local
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, path, method='GET'):
        # Destinos fijos. Nunca aceptar una URL procedente de las notas o un adjunto.
        if not path.startswith('/repos/') or '..' in path or '?' in path.split('/repos/', 1)[0]:
            raise ValueError('Ruta de API no autorizada')
        repository = '/'.join(path.split('/')[2:4])
        if repository not in (GITHUB_REPOS if self.forge == 'github' else (FORGEJO_REPO,)):
            raise ValueError('Repositorio fuera del ámbito de limpieza')
        if method not in ('GET', 'DELETE'):
            raise ValueError('Método de API no autorizado')
        if method == 'DELETE' and (not self.token or not re.fullmatch(r'/repos/[^/]+/[^/]+/releases/[1-9][0-9]*', path)):
            raise ValueError('Solo se permite borrar una release identificada; nunca repositorios o Git')
        headers = {'Accept': 'application/json', 'User-Agent': 'hgw-release-retention'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request(self.base + path, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=90) as response:
                if method == 'DELETE':
                    if response.status != 204:
                        raise ValueError('La API no confirmó el borrado')
                    return None
                if 'application/json' not in response.headers.get('Content-Type', ''):
                    raise ValueError('La API no devolvió JSON')
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError('Respuesta de API demasiado grande')
                return json.loads(raw)
        except urllib.error.HTTPError as error:
            error.close()
            # No imprimir cabeceras, cuerpo ni errores remotos que puedan contener secretos.
            raise ValueError('Fallo de API ' + self.forge + ': HTTP ' + str(error.code)) from None
        except urllib.error.URLError:
            raise ValueError('No se puede conectar con la API ' + self.forge) from None

    def releases(self, repository):
        result = []
        parameter = 'per_page' if self.forge == 'github' else 'limit'
        for page in range(1, 101):
            batch = self.request(f'/repos/{repository}/releases?{parameter}=50&page={page}')
            if not isinstance(batch, list):
                raise ValueError('Listado de releases no válido')
            result.extend(batch)
            if len(batch) < 50:
                ids = [r['id'] for r in result]
                if len(set(ids)) != len(ids):
                    raise ValueError('La paginación cambió; repetir sin borrar')
                return result
        raise ValueError('Listado incompleto; no se permite limpiar')


def version(tag, repository):
    patterns = ['v' + VERSION]
    if repository.endswith('/headscale_gateway_ynh'):
        patterns += ['v' + VERSION + r'-ynh[1-9][0-9]*', 'server-v' + VERSION]
    for pattern in patterns:
        match = re.fullmatch(pattern, tag)
        if match:
            return tuple(map(int, match.groups()[:3]))
    return None


def stable(release):
    return release.get('draft') is False and release.get('prerelease') is False


def signature(release):
    # Los contadores de descargas cambian normalmente; el contenido no debe cambiar.
    value = {key: release.get(key) for key in ('id', 'tag_name', 'draft', 'prerelease', 'body', 'immutable')}
    value['assets'] = sorted((a['id'], a['name'], a['size'], a.get('digest')) for a in release.get('assets', []))
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def public_bytes(url):
    # Solo recibe URL construida aquí: descargas anónimas, sin el token de la API.
    with urllib.request.urlopen(url, timeout=90) as response:
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Manifiesto público demasiado grande')
        return raw


def verify_completed(api, release):
    tag = release['tag_name']
    assets = {a['name']: a for a in release.get('assets', [])}
    if 'SHA256SUMS' not in assets or len(assets) < 2:
        raise ValueError('La entrega que se conserva no tiene sumas e instaladores')
    raw = public_bytes(f'https://github.com/{GENERAL}/releases/download/{tag}/SHA256SUMS')
    if assets['SHA256SUMS'].get('digest') != 'sha256:' + hashlib.sha256(raw).hexdigest():
        raise ValueError('Las sumas de la entrega que se conserva están alteradas')
    sums = {}
    for line in raw.decode().splitlines():
        value, name = line.split(maxsplit=1)
        if name in sums or not re.fullmatch('[0-9a-f]{64}', value) or Path(name).name != name:
            raise ValueError('Manifiesto público no válido')
        sums[name] = value
    if set(sums) != set(assets) - {'SHA256SUMS'}:
        raise ValueError('La entrega conservada está incompleta')
    if any(assets[name].get('digest') != 'sha256:' + value for name, value in sums.items()):
        raise ValueError('Los adjuntos conservados difieren de sus sumas')
    v = tag[1:]
    for repository, suffix in [(GITHUB_REPOS[1], ''), (GITHUB_REPOS[2], '-ynh1'), (GITHUB_REPOS[3], '')]:
        other = api.request(f'/repos/{repository}/releases/tags/v{v}{suffix}')
        if not stable(other) or not other.get('assets'):
            raise ValueError('Falta una distribución de la entrega conservada')


def keep_versions(public):
    releases = public.releases(GENERAL)
    completed = [r for r in releases if stable(r) and version(r['tag_name'], GENERAL) is not None
                 and MARKER.search(r.get('body') or '')]
    completed.sort(key=lambda r: version(r['tag_name'], GENERAL), reverse=True)
    if len(completed) < 2:
        raise ValueError('Se necesitan dos entregas públicas completas antes de borrar')
    chosen = completed[:2]
    for release in chosen:
        verify_completed(public, release)
    return [version(r['tag_name'], GENERAL) for r in chosen]


def plan(target, public):
    keep = keep_versions(public)
    cutoff = min(keep)
    repositories = GITHUB_REPOS if target.forge == 'github' else (FORGEJO_REPO,)
    deletions, protected = [], []
    # Primero terminar todas las lecturas. Un error evita cualquier borrado.
    for repository in repositories:
        for release in target.releases(repository):
            tag = release['tag_name']
            v = version(tag, repository)
            # Fuentes compartidos: nunca se borran automáticamente, aunque dejen de
            # estar referenciados en Latest. Pueden sostener redistribuciones anteriores.
            if not stable(release) or v is None or v >= cutoff or release.get('immutable'):
                protected.append({'repository': repository, 'tag': tag})
                continue
            if not isinstance(release['id'], int) or release['id'] <= 0:
                raise ValueError('Identificador de release no válido')
            deletions.append({'repository': repository, 'tag': tag, 'id': release['id'],
                              'signature': signature(release),
                              'bytes': sum(a['size'] for a in release.get('assets', []))})
    return {'format': 1, 'forge': target.forge, 'keep_versions': ['.'.join(map(str, v)) for v in keep],
            'delete': sorted(deletions, key=lambda x: (x['repository'], x['id'])), 'protected': protected}


def execute(target, report):
    removed = []
    # Precondiciones de todo el lote antes de empezar; nueva comprobación por elemento
    # reduce la ventana de carrera. No hay operación de borrado de etiquetas.
    for item in report['delete']:
        current = target.request(f"/repos/{item['repository']}/releases/{item['id']}")
        if signature(current) != item['signature']:
            raise ValueError('Una release cambió desde el plan; no se inicia la limpieza')
    for item in report['delete']:
        path = f"/repos/{item['repository']}/releases/{item['id']}"
        if signature(target.request(path)) != item['signature']:
            raise ValueError('Una release cambió durante la limpieza; se detiene')
        target.request(path, 'DELETE')
        removed.append({key: item[key] for key in ('repository', 'tag', 'id', 'bytes')})
        print('RELEASE_RETIRADA: ' + item['repository'] + ' ' + item['tag'], flush=True)
    return removed


def token_for_forgejo():
    folder = os.environ.get('CREDENTIALS_DIRECTORY')
    path = Path(folder) / 'forgejo-token' if folder else Path('/etc/hgw-release-retention/forgejo-token')
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('La credencial debe estar protegida y no ser un enlace')
    token = path.read_text().strip()
    if not token or '\n' in token or '\r' in token:
        raise ValueError('Credencial local no válida')
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forge', choices=('github', 'forgejo'), required=True)
    parser.add_argument('--apply', action='store_true', help='Sin esta opción solo prepara un plan')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    public = API('github', os.environ.get('GH_TOKEN', ''))
    target = public if args.forge == 'github' else API('forgejo', token_for_forgejo())
    if args.apply and not target.token:
        raise ValueError('El borrado requiere la credencial limitada del destino')
    report = plan(target, public)
    print(json.dumps(report, indent=2), flush=True)
    report['removed'] = execute(target, report) if args.apply else []
    report['applied'] = args.apply
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('RETENCION_OK: ' + args.forge + '; conservadas ' + ', '.join(report['keep_versions']), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        print('RETENCION_BLOQUEADA: no se pudo validar o completar la limpieza; revisar API, permisos y estado.', file=sys.stderr)
        sys.exit(1)

