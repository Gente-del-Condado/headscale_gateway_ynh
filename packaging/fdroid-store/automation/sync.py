#!/usr/bin/env python3
"""Tienda binaria propia: verifica APK públicas y firma exclusivamente su índice."""
import argparse
import base64
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
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r'[0-9a-fA-F]{64}')
TAG = re.compile(r'v(\d+)\.(\d+)\.(\d+)')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(url):
    # Todo es público. No se transmite ningún token a descargas ni redirecciones.
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Gente-del-Condado-FDroid'}), timeout=45) as response:
        return json.load(response)


def settings(root=ROOT):
    value = json.loads((root / 'store.json').read_text())
    if value['format'] != 1 or not 1 <= value['keep_versions'] <= 5:
        raise ValueError('Formato o retención no válidos')
    if not HEX.fullmatch(value['index_certificate_sha256']):
        raise ValueError('Falta la huella estable del índice')
    if not value['url'].startswith('https://') or '?' in value['url']:
        raise ValueError('La tienda requiere una URL HTTPS sin parámetros')
    if not value['apps']:
        raise ValueError('La tienda no puede quedar vacía por accidente')
    seen = set()
    for app in value['apps']:
        if not re.fullmatch(r'[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+', app['id']) or app['id'] in seen:
            raise ValueError('Identificador de aplicación inválido o duplicado')
        seen.add(app['id'])
        if not re.fullmatch(r'Gente-del-Condado/[A-Za-z0-9_.-]+', app['source_repository']):
            raise ValueError('Solo se admiten orígenes públicos propios declarados')
        if not HEX.fullmatch(app['certificate_sha256']):
            raise ValueError('Cada aplicación necesita una firma fijada')
        for field in ('apk_asset', 'verification_asset'):
            if Path(app[field]).name != app[field] or not re.fullmatch(r'[A-Za-z0-9_.-]+', app[field]):
                raise ValueError('Nombre de adjunto no válido')
    return value


def release_assets(release, app):
    tag = release['tag_name']
    if release['draft'] or release['prerelease'] or not TAG.fullmatch(tag):
        return None
    assets = {item['name']: item for item in release['assets']}
    required = (app['apk_asset'], app['verification_asset'], 'SHA256SUMS')
    if not all(name in assets for name in required):
        return None  # Una release todavía incompleta no entra en la tienda.
    prefix = f"https://github.com/{app['source_repository']}/releases/download/{tag}/"
    for name in required:
        if assets[name]['browser_download_url'] != prefix + name:
            raise ValueError('Un adjunto no pertenece al origen y etiqueta declarados')
    return assets


def validate_report(report, app, tag):
    if (report['package'] != app['id'] or report['version'] != tag[1:]
            or report.get('debuggable', True) or report.get('unsigned', True)
            or report['certificate_sha256'].lower() != app['certificate_sha256'].lower()
            or not HEX.fullmatch(report['sha256'])
            or type(report['version_code']) is not int or report['version_code'] <= 0):
        raise ValueError('La APK no coincide con la identidad y firma de producción')


def configuration_digest(root):
    rows = []
    for path in sorted(root.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and '.git' not in path.parts:
            rows.append(path.relative_to(root).as_posix() + ':' + digest(path))
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()


def plan(config, root=ROOT):
    packages = []
    for app in config['apps']:
        releases = read_json(f"https://api.github.com/repos/{app['source_repository']}/releases?per_page=100")
        candidates = [r for r in releases if not r['draft'] and not r['prerelease'] and TAG.fullmatch(r['tag_name'])]
        candidates.sort(key=lambda r: tuple(map(int, TAG.fullmatch(r['tag_name']).groups())), reverse=True)
        selected = []
        for release in candidates:
            assets = release_assets(release, app)
            if assets is None:
                continue
            report = read_json(assets[app['verification_asset']]['browser_download_url'])
            validate_report(report, app, release['tag_name'])
            selected.append({'app': app['id'], 'tag': release['tag_name'], 'version': report['version'],
                             'version_code': report['version_code'], 'sha256': report['sha256'],
                             'url': assets[app['apk_asset']]['browser_download_url'],
                             'sums_url': assets['SHA256SUMS']['browser_download_url']})
            if len(selected) == config['keep_versions']:
                break
        if not selected:
            raise ValueError('No hay una release completa y verificable para ' + app['id'])
        codes = [p['version_code'] for p in selected]
        if len(set(codes)) != len(codes) or codes != sorted(codes, reverse=True):
            raise ValueError('Los códigos Android no crecen con las versiones')
        packages.extend(selected)
    body = {'format': 1, 'configuration_sha256': configuration_digest(root), 'packages': packages}
    body['plan_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def needs_update(proposed, previous, now=None):
    now = int(time.time()) if now is None else now
    for app in {p['app'] for p in proposed.get('packages', [])}:
        current = max(p['version_code'] for p in proposed['packages'] if p['app'] == app)
        older = [p['version_code'] for p in previous.get('packages', []) if p['app'] == app]
        if older and current < max(older):
            raise ValueError('El origen ha retrocedido; se conserva la tienda publicada')
    # Aunque no haya APK nuevas se renueva semanalmente el índice firmado.
    return (previous.get('plan_sha256') != proposed['plan_sha256']
            or not 0 <= now - previous.get('generated_at', 0) < 7 * 86400)


def download(url, destination, limit):
    with urllib.request.urlopen(url, timeout=90) as source, destination.open('xb') as out:
        size = 0
        while chunk := source.read(1 << 20):
            size += len(chunk)
            if size > limit:
                raise ValueError('Adjunto demasiado grande')
            out.write(chunk)


def check_apk(path, item, app, sdk):
    if digest(path) != item['sha256']:
        raise ValueError('La APK descargada no coincide con SHA-256')
    tools = Path(sdk) / 'build-tools' / '35.0.0'
    env = dict(os.environ, LC_ALL='C.UTF-8')
    signed = subprocess.run([str(tools / 'apksigner'), 'verify', '--print-certs', str(path)], env=env, capture_output=True, text=True, check=True)
    signers = re.findall(r'Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-fA-F]{64})', signed.stdout)
    if len(signers) != 1 or signers[0].lower() != app['certificate_sha256'].lower():
        raise ValueError('La firma real de la APK ha cambiado')
    badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(path)], env=env, text=True)
    actual = re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badging)
    if (not actual or actual[1] != app['id'] or int(actual[2]) != item['version_code']
            or actual[3] != item['version'] or 'application-debuggable' in badging):
        raise ValueError('El manifiesto real de la APK no coincide')


def copy_app_icon(root, metadata, app_id):
    # El catálogo necesita un PNG independiente del icono adaptativo de la APK.
    relative = Path(app_id) / 'en-US/images/icon.png'
    source = root / 'metadata' / relative
    if source.is_symlink() or not source.is_file():
        raise ValueError('Falta el PNG de catálogo para ' + app_id)
    target = metadata / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def verify_icons(repo, packages):
    for app in packages.values():
        icons = app['metadata'].get('icon', {})
        if not icons:
            raise ValueError('El índice no contiene el icono de una aplicación')
        for icon in icons.values():
            path = (repo / icon['name'].lstrip('/')).resolve()
            if (repo.resolve() not in path.parents or not path.is_file()
                    or digest(path) != icon['sha256'] or path.stat().st_size != icon['size']):
                raise ValueError('El icono del catálogo no coincide con el índice firmado')


def verify_index(repo, fingerprint, expected):
    from fdroidserver import common, index
    common.config = dict(common.default_config, jarsigner=str(Path(os.environ['JAVA_HOME']) / 'bin/jarsigner'))
    entry, _key, _fingerprint = index.get_index_from_jar(str(repo / 'entry.jar'), fingerprint)
    payload = repo / 'index-v2.json'
    if entry['index']['sha256'] != digest(payload):
        raise ValueError('El índice v2 no coincide con su entrada firmada')
    value = json.loads(payload.read_text())
    verify_icons(repo, value['packages'])
    actual = {}
    for app_id, app in value['packages'].items():
        for version in app['versions'].values():
            manifest = version['manifest']
            actual[(app_id, manifest['versionCode'])] = version['file']['sha256']
    wanted = {(item['app'], item['version_code']): item['sha256'] for item in expected}
    if actual != wanted:
        raise ValueError('El índice no contiene exactamente las APK comprobadas')
    # El índice v1 conserva compatibilidad con clientes anteriores.
    index.get_index_from_jar(str(repo / 'index-v1.jar'), fingerprint, allow_deprecated=True)


def build(config, proposed, output, sdk, signing, root=ROOT):
    if proposed['configuration_sha256'] != configuration_digest(root):
        raise ValueError('Las fuentes de la tienda cambiaron después del plan')
    if output.exists() or output.is_symlink():
        raise ValueError('El sitio de salida debe ser nuevo')
    apps = {a['id']: a for a in config['apps']}
    with tempfile.TemporaryDirectory(prefix='fdroid-private-') as temporary:
        work = Path(temporary); repo = work / 'repo'; repo.mkdir()
        keys = work / 'keys'; keys.mkdir(mode=0o700)
        key = keys / 'repo.jks'; key.touch(mode=0o600); key.write_bytes(base64.b64decode(signing['keystore_base64'], validate=True))
        env = dict(os.environ, FDROID_KEY_STORE_PASS=signing['store_password'])
        certificate = subprocess.check_output([str(Path(env['JAVA_HOME'])/'bin/keytool'), '-exportcert', '-keystore', str(key), '-alias', 'fdroid-repo', '-storepass:env', 'FDROID_KEY_STORE_PASS'], env=env, stderr=subprocess.DEVNULL)
        if hashlib.sha256(certificate).hexdigest().upper() != config['index_certificate_sha256'].upper():
            raise ValueError('La clave no corresponde a la identidad estable de la tienda')
        for item in proposed['packages']:
            app = apps[item['app']]
            apk = repo / f"{app['id']}_{item['version_code']}.apk"
            download(item['url'], apk, 512 << 20)
            sums = work / (apk.stem + '.sums'); download(item['sums_url'], sums, 1 << 20)
            expected = [line.split() for line in sums.read_text().splitlines() if len(line.split()) == 2 and line.split()[1] == app['apk_asset']]
            if len(expected) != 1 or expected[0][0] != item['sha256']:
                raise ValueError('Las sumas de la release no coinciden con la APK')
            check_apk(apk, item, app, sdk)
        metadata = work / 'metadata'; metadata.mkdir()
        for app_id, app in apps.items():
            versions = [p for p in proposed['packages'] if p['app'] == app_id]
            newest = max(versions, key=lambda p: p['version_code'])
            info = {'Categories': ['Connectivity'], 'License': app['license'], 'AuthorName': 'Gente del Condado',
                    'AuthorEmail': 'headscale-gateway@gentedelcondado.es', 'WebSite': app['website'],
                    'SourceCode': app['source_code'], 'IssueTracker': app['issue_tracker'],
                    'Name': app['name'], 'Summary': app['summary'], 'Description': app['description'],
                    'CurrentVersion': newest['version'], 'CurrentVersionCode': newest['version_code'],
                    'AllowedAPKSigningKeys': [app['certificate_sha256']]}
            copy_app_icon(root, metadata, app_id)
            (metadata / (app_id+'.yml')).write_text(json.dumps(info, ensure_ascii=False, indent=2))
        shutil.copy2(root / 'repo-icon.png', work / 'repo-icon.png')
        private_config = {'repo_url': config['url'], 'repo_name': config['name'], 'repo_description': config['description'],
                          'repo_icon': 'repo-icon.png', 'repo_keyalias': 'fdroid-repo', 'keystore': str(key),
                          'keystorepass': signing['store_password'], 'keypass': signing['key_password'],
                          'sdk_path': str(Path(sdk).resolve()), 'build_tools': '35.0.0',
                          'archive_older': 0, 'make_current_version_link': False, 'repo_maxage': 14*86400}
        path = work / 'config.yml'; path.touch(mode=0o600); path.write_text(json.dumps(private_config))
        result = subprocess.run(['fdroid', 'update', '--use-date-from-apk'], cwd=work, capture_output=True, text=True)
        if result.returncode:
            # Los diagnósticos del generador nunca incluyen su configuración privada.
            raise RuntimeError('fdroid update no completó la generación del índice (código '+str(result.returncode)+')')
        verify_index(repo, config['index_certificate_sha256'], proposed['packages'])
        output.mkdir(parents=True)
        target = output / 'fdroid/repo'; target.parent.mkdir()
        for p in repo.rglob('*'):
            if p.is_symlink() or (p.is_file() and p.suffix.lower() not in {'.apk','.jar','.xml','.json','.html','.css','.png','.jpg','.jpeg','.webp','.asc','.gz','.svg'}):
                raise ValueError('El generador produjo un archivo inesperado; no se publica')
        shutil.copytree(repo, target)
        receipt = dict(proposed, generated_at=int(time.time()))
        (target / 'store-state.json').write_text(json.dumps(receipt, indent=2)+'\n')
        (output / '.nojekyll').touch()
        shutil.copy2(root / 'LICENSE', output / 'LICENSE')
        print('FDROID_INDICES_VERIFICADOS_OK: firma estable, índices v1/v2 y APK originales')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--signing-profile', type=Path, help='Bundle privado local; en Actions se usa el secreto')
    args = parser.parse_args()
    config = settings(); args.work.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.plan:
        proposed = plan(config)
        try:
            previous = read_json(config['url'] + '/store-state.json')
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
            previous = {}
        changed = needs_update(proposed, previous)
        (args.work / 'plan.json').write_text(json.dumps(proposed, indent=2)+'\n')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as stream: stream.write('changed='+str(changed).lower()+'\n')
        print('FDROID_PLAN: '+str(len(proposed['packages']))+' APK verificables; cambios='+str(changed).lower())
        return
    if not args.sdk: parser.error('--sdk es obligatorio para construir el índice')
    if args.signing_profile:
        if args.signing_profile.is_symlink() or args.signing_profile.stat().st_mode & 0o077:
            raise ValueError('El perfil local debe ser un archivo privado normal')
        signing = json.loads(args.signing_profile.read_text())
    else:
        signing = json.loads(os.environ['FDROID_REPO_SIGNING_BUNDLE'])
    build(config, json.loads((args.work/'plan.json').read_text()), args.work/'site', args.sdk, signing)


if __name__ == '__main__':
    main()
