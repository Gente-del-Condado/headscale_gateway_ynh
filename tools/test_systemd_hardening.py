#!/usr/bin/env python3
"""Aceptación optativa en un laboratorio con systemd real; no usa datos activos."""
import argparse
import ctypes
import errno
import mmap
import os
from pathlib import Path
import pwd
import shutil
import socket
import sqlite3
import ssl
import subprocess
import tempfile


def probe(data, outside):
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    assert int(status['CapBnd'].strip(), 16) == 0, 'Hay capacidades disponibles'
    assert status['NoNewPrivs'].strip() == '1'
    assert status['Seccomp'].strip() == '2'
    try:
        with mmap.mmap(-1, mmap.PAGESIZE, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC):
            pass
    except OSError as error:
        assert error.errno in (errno.EPERM, errno.EACCES)
    else:
        raise AssertionError('Se permite memoria escribible y ejecutable')
    libc = ctypes.CDLL(None, use_errno=True)
    assert libc.unshare(0x10000000) == -1 and ctypes.get_errno() == errno.EPERM, 'Se permite crear un namespace de usuario'
    try:
        (outside / 'write-denied').write_text('lab')
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
    else:
        raise AssertionError('Se permite escribir fuera de los datos')
    with sqlite3.connect(data / 'probe.sqlite') as db:
        assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
        db.execute('CREATE TABLE probe (value TEXT)')
        db.execute('INSERT INTO probe VALUES (?)', ('lab',))
        assert db.execute('SELECT value FROM probe').fetchone()[0] == 'lab'
    ssl.create_default_context()
    assert socket.getaddrinfo('localhost', 80)
    for family, kind in ((socket.AF_UNIX, socket.SOCK_STREAM), (socket.AF_INET, socket.SOCK_DGRAM),
                         (socket.AF_INET6, socket.SOCK_STREAM), (socket.AF_NETLINK, socket.SOCK_RAW)):
        with socket.socket(family, kind):
            pass
    subprocess.run(['getent', 'group', 'nogroup' if shutil.which('dpkg') else 'nobody'], check=True, stdout=subprocess.DEVNULL)
    print('AISLAMIENTO_OK: capacidades vacías, NNP, seccomp, W^X, namespaces y escritura restringidos; SQLite WAL, TLS, NSS y sockets permitidos', flush=True)


def acceptance(template, tests, user=False, lab_root=None):
    if not user and os.geteuid() != 0:
        raise ValueError('Ejecuta solo con root en un laboratorio autorizado')
    account = pwd.getpwuid(os.getuid()) if user else pwd.getpwnam('nobody')
    root = Path(tempfile.mkdtemp(prefix='hgw-security-lab-', dir=lab_root if user else '/var/lib'))
    unit = root.name + '.service'
    unit_file = (Path(os.environ['XDG_RUNTIME_DIR'])/'systemd/user' if user else Path('/run/systemd/system')) / unit
    unit_file.parent.mkdir(parents=True, exist_ok=True)
    systemctl = ['systemctl', '--user'] if user else ['systemctl']
    try:
        root.chmod(0o755)
        data = root / 'data'; data.mkdir(mode=0o700); os.chown(data, account.pw_uid, account.pw_gid)
        outside = root / 'outside'; outside.mkdir(mode=0o777); outside.chmod(0o777)
        for source, name in ((Path(__file__).resolve(), 'probe.py'), (tests.resolve(), 'gateway.test')):
            shutil.copy2(source, root / name); (root / name).chmod(0o755)
        text = template.read_text().replace('__APP__', 'nobody').replace('__INSTALL_DIR__', str(root)).replace('__DATA_DIR__', str(data))
        text = text.replace('User=headscale-gateway', 'User=nobody').replace('Group=headscale-gateway', 'Group='+account.pw_name)
        text = text.replace('Group=nobody', 'Group='+str(account.pw_gid)).replace('User=gateway', 'User=nobody').replace('Group=gateway', 'Group='+str(account.pw_gid))
        text = text.replace('/var/lib/headscale-gateway', str(data))
        lines = [line for line in text.splitlines() if not line.startswith(('ExecStart=', 'ExecCondition=', 'StateDirectory=', 'StateDirectoryMode=', 'RuntimeDirectory=', 'RuntimeDirectoryMode=', 'Restart=', 'Type='))]
        if user:
            lines = [line for line in lines if not line.startswith(('User=', 'Group='))]
            lines.insert(lines.index('[Service]')+1, 'PrivateUsers=yes')
        index = lines.index('[Service]') + 1
        lines[index:index] = ['Type=oneshot', 'Restart=no', 'TimeoutStartSec=180',
            f'ExecStartPre=/usr/bin/python3 {root}/probe.py --probe {data} {outside}',
            f'ExecStart={root}/gateway.test -test.v -test.run=Technitium|RetiredNodeDNS|Restore|DNS|LocalCertificateRealTLS']
        unit_file.write_text('\n'.join(lines)+'\n')
        subprocess.run(systemctl + ['daemon-reload'], check=True)
        result = subprocess.run(systemctl + ['start', unit])
        subprocess.run(['journalctl', *(['--user'] if user else []), '-u', unit, '--no-pager', '-o', 'cat'], check=True)
        result.check_returncode()
        print('SYSTEMD_ACEPTACION_OK: '+template.name)
    finally:
        subprocess.run(systemctl + ['stop', unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        unit_file.unlink(missing_ok=True)
        subprocess.run(systemctl + ['daemon-reload'], check=True)
        subprocess.run(systemctl + ['reset-failed', unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-disposable-lab', action='store_true')
    parser.add_argument('--template', type=Path)
    parser.add_argument('--tests', type=Path)
    parser.add_argument('--user', action='store_true', help='Prueba de sesión con PrivateUsers; no sustituye una instalación de sistema')
    parser.add_argument('--lab-root', type=Path, help='Directorio visible en el sandbox de la sesión')
    parser.add_argument('--probe', nargs=2, type=Path)
    args = parser.parse_args()
    if args.user and not args.lab_root:
        parser.error("--user requiere --lab-root fuera del directorio temporal privado")
    if args.probe:
        probe(*args.probe)
    elif args.confirm_disposable_lab and args.template and args.tests:
        acceptance(args.template, args.tests, args.user, args.lab_root)
    else:
        parser.error('Se requiere confirmar el laboratorio y proporcionar plantilla y binario de pruebas')
