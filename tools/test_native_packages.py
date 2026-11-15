#!/usr/bin/env python3
"""Aceptación aislada de .deb y .rpm; no instala paquetes en el host."""
from pathlib import Path
import argparse,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
root=a.directory.resolve()
for image,kind,pattern,install,remove in [
    ('debian:12','deb','*_amd64.deb','apt-get update && apt-get install -y python3 systemd curl && dpkg -i /packages/*.deb','dpkg -r headscale-gateway'),
    ('fedora:44','rpm','*.x86_64.rpm','dnf install -y python3 systemd util-linux && rpm -i /packages/*.rpm','rpm -e headscale-gateway')]:
    files=list(root.glob(pattern))
    if len(files)!=1:raise SystemExit('No se ha encontrado un único paquete '+kind)
    # Solo se monta la copia exacta del paquete objetivo; no se usa la red del host.
    mount=files[0].parent/('test-'+kind);mount.mkdir(exist_ok=True)
    import shutil
    shutil.copy2(files[0],mount/files[0].name)
    script=f'''set -eu
{install}
/usr/bin/headscale-gateway --help > /tmp/help.txt
id headscale-gateway
runuser -u headscale-gateway -- sh -c 'umask 077; mkdir -p /var/lib/headscale-gateway/gateway /var/lib/headscale-gateway/config; printf fixture-secret > /var/lib/headscale-gateway/gateway/master.key; printf fixture-state > /var/lib/headscale-gateway/gateway/fixture.sqlite; printf fixture-startup > /var/lib/headscale-gateway/config/startup.json'
sha256sum /var/lib/headscale-gateway/gateway/* /var/lib/headscale-gateway/config/* > /tmp/preserved
'''
    script+=('dpkg -i /packages/*.deb\n' if kind=='deb' else 'rpm -U --replacepkgs /packages/*.rpm\n')
    script+='sha256sum -c /tmp/preserved\n'+remove+'\nsha256sum -c /tmp/preserved\n'
    subprocess.run(['docker','run','--rm','--cpus','2','--memory','2g','-v',str(mount)+':/packages:ro',image,'sh','-ec',script],check=True)
    shutil.rmtree(mount)
print('PAQUETES_NATIVOS_OK: instalación, reinstalación y conservación tras desinstalar')
