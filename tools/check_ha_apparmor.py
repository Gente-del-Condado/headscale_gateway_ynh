#!/usr/bin/env python3
"""Aceptación AppArmor en una aplicación HA desechable; nunca usar datos activos."""
import argparse
import http.client
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile


def confinement():
    """Ejecutar mediante docker exec dentro de la copia de laboratorio."""
    profile = Path('/proc/self/attr/current').read_text().strip()
    assert '_headscale_gateway_apparmor_lab (enforce)' in profile, profile
    assert Path('/data/.hgw-apparmor-lab').is_file(), 'Falta la marca del laboratorio aislado'
    for path, mode in (('/etc/shadow', 'rb'), ('/usr/local/bin/.hgw-denied', 'wb')):
        try:
            with open(path, mode):
                pass
        except PermissionError:
            pass
        else:
            raise AssertionError('AppArmor permitió acceso a ' + path)
    try:
        subprocess.run(['/bin/sh', '-c', 'exit 0'], check=True)
    except PermissionError:
        pass
    else:
        raise AssertionError('AppArmor permitió ejecutar una shell')
    # SQLite real con bloqueo y memoria compartida, sin abrir la base del Gateway.
    with tempfile.TemporaryDirectory(prefix='.apparmor-check-', dir='/data') as directory:
        db = sqlite3.connect(str(Path(directory) / 'probe.sqlite'))
        try:
            assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
            db.execute('CREATE TABLE probe (value TEXT)')
            db.execute('INSERT INTO probe VALUES (?)', ('lab-only',))
            db.commit()
            assert db.execute('SELECT value FROM probe').fetchone()[0] == 'lab-only'
        finally:
            db.close()
    with tempfile.TemporaryDirectory(prefix='hgw-apparmor-') as directory:
        Path(directory, 'probe').write_text('temporary')
    # El descubrimiento utiliza UDP multicast; no necesita sockets IP raw.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.bind(('', 0))
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                       socket.inet_aton('239.255.42.91') + socket.inet_aton('0.0.0.0'))
    assert socket.getaddrinfo('supervisor', 80), 'Falló el resolver del contenedor'
    print('OK: enforce; SQLite WAL, temporales, DNS y multicast; shadow, escritura de programas y shell bloqueados')


def panel(address):
    """Ejecutar dentro de Supervisor para probar su origen Ingress real."""
    host, port = address.rsplit(':', 1)
    headers = {'X-Ingress-Path': '/api/hassio_ingress/apparmor-lab',
               'Host': 'ha.test', 'Origin': 'https://ha.test', 'X-Forwarded-Proto': 'https',
               'X-Remote-User-Id': 'apparmor-lab-admin',
               'X-Remote-User-Groups': 'system-admin,system-users', 'Content-Type': 'application/json'}

    def request(method, path, body=None, expected=200, extra=None):
        connection = http.client.HTTPConnection(host, int(port), timeout=35)
        try:
            connection.request(method, path, json.dumps(body) if body is not None else None,
                               dict(headers, **(extra or {})))
            response = connection.getresponse()
            data = response.read()
            assert response.status == expected, f'{method} {path}: HTTP {response.status}, esperado {expected}'
            return json.loads(data) if data[:1] in (b'{', b'[') else data
        finally:
            connection.close()

    session = request('GET', '/api/v1/auth/session')
    assert session['source'] == 'proxy' and session['role'] == 'admin'
    assert session['user'] == 'proxy:apparmor-lab-admin'
    request('POST', '/api/v1/reload', {}, expected=401)
    headers['X-CSRF-Token'] = session['csrf']
    request('GET', '/api/v1/status', expected=403,
            extra={'X-Remote-User-Groups': 'system-users'})
    for path in ('/admin/', '/admin/http-paths.js', '/api/v1/status', '/api/v1/pki',
                 '/api/v1/pki/discover', '/api/v1/backups'):
        request('GET', path)
    # Credencial ficticia exclusiva del ensayo, nunca de una instalación real.
    password = 'apparmor-lab-backup-password-strong'
    settings = request('GET', '/api/v1/backups')
    # La copia de laboratorio puede conservar la clave de un ensayo anterior.
    if not settings.get('encryption_configured', False):
        # 409 solo indica que ya existe la clave; no se sobrescribe.
        connection = http.client.HTTPConnection(host, int(port), timeout=35)
        try:
            connection.request('POST', '/api/v1/backups/encryption', json.dumps({'password': password}), headers)
            response = connection.getresponse(); response.read()
            assert response.status in (200, 409), 'No se pudo preparar el cifrado del laboratorio'
        finally:
            connection.close()
    backup = request('POST', '/api/v1/backups',
                     {'password': password, 'components': {'sqlite': True}}, expected=201)
    assert len(request('GET', '/api/v1/backups/' + backup['id'] + '/download')) > 100
    exported = request('POST', '/api/v1/config/transfer/export', {'password': password, 'secrets': True})
    assert exported['filename'].endswith('.hgwcfg') and exported['data']
    print('OK: Ingress/SSO, CSRF y rechazo no-admin; panel, PKI, descubrimiento, copia cifrada y exportación')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-disposable-lab', action='store_true', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--confinement', action='store_true')
    mode.add_argument('--panel-address', metavar='HOST:PORT')
    args = parser.parse_args()
    if args.confinement:
        confinement()
    else:
        panel(args.panel_address)


if __name__ == '__main__':
    main()
