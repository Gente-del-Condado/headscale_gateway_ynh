#!/usr/bin/env python3
"""Empaqueta binarios ya comprobados del Gateway, sin compilarlos ni tocar el host."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def stage(destination, binary, helper):
    destination=Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('El destino debe estar vacío')
    destination.mkdir(parents=True,exist_ok=True)
    def copy(source, target, mode=0o644):
        source=Path(source)
        if source.is_symlink() or not source.is_file(): raise ValueError('Archivo de origen no válido')
        path=destination/target;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,path);path.chmod(mode)
    for source,target,mode in [(binary,'usr/libexec/headscale-gateway/headscale-gateway',0o755),
        (helper,'usr/libexec/headscale-gateway/hgw-ca-helper',0o755),
        (ROOT/'packaging/linux/native/headscale-gateway.service','usr/lib/systemd/system/headscale-gateway.service',0o644),
        (ROOT/'packaging/linux/native/headscale-gateway.sysusers','usr/lib/sysusers.d/headscale-gateway.conf',0o644),
        (ROOT/'packaging/linux/native/headscale-gateway.tmpfiles','usr/lib/tmpfiles.d/headscale-gateway.conf',0o644),
        (ROOT/'packaging/linux/native/headscale-gateway-configure','usr/bin/headscale-gateway-configure',0o755),
        (ROOT/'packaging/linux/native/headscale-gateway-open-admin','usr/bin/headscale-gateway-open-admin',0o755),
        (ROOT/'packaging/linux/native/es.gentedelcondado.HeadscaleGateway.desktop','usr/share/applications/es.gentedelcondado.HeadscaleGateway.desktop',0o644),
        (ROOT/'packaging/flatpak/files/es.gentedelcondado.HeadscaleGateway.png','usr/share/icons/hicolor/128x128/apps/es.gentedelcondado.HeadscaleGateway.png',0o644),
        (ROOT/'packaging/common/hgw_bootstrap.py','usr/libexec/headscale-gateway/hgw_bootstrap.py',0o644),
        (ROOT/'packaging/linux/README.md','usr/share/doc/headscale-gateway/README.md',0o644),
        (ROOT/'LICENSE','usr/share/licenses/headscale-gateway/LICENSE',0o644),
        (ROOT/'NOTICE','usr/share/licenses/headscale-gateway/NOTICE',0o644)]:copy(source,target,mode)
    (destination/'usr/bin/headscale-gateway').symlink_to('../libexec/headscale-gateway/headscale-gateway')
    copy(ROOT/'LICENSE','usr/share/doc/headscale-gateway/copyright')
    from package_platforms import add_notices
    add_notices(destination/'usr/share/licenses/headscale-gateway/notices')


POST='''#!/bin/sh
set -eu
systemd-sysusers /usr/lib/sysusers.d/headscale-gateway.conf
systemd-tmpfiles --create /usr/lib/tmpfiles.d/headscale-gateway.conf
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
    systemctl try-restart headscale-gateway.service
fi
'''
PRE='''#!/bin/sh
set -eu
if [ -f /var/lib/headscale-gateway/gateway.sqlite ]; then
    echo 'Instalación manual detectada: migra explícitamente antes de instalar este paquete.' >&2
    exit 1
fi
'''
REMOVE='''#!/bin/sh
set -eu
case "${1:-}" in
    remove|0)
        if [ -d /run/systemd/system ]; then systemctl stop headscale-gateway.service; fi
        ;;
esac
'''


def build(output,binary,helper,arch,kind):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip()
    with tempfile.TemporaryDirectory(prefix='hgw-native-package-') as temporary:
        base=Path(temporary);root=base/'root';stage(root,binary,helper)
        if kind=='deb':
            control=root/'DEBIAN';control.mkdir()
            (control/'control').write_text(f'Package: headscale-gateway\nVersion: {version}-1\nArchitecture: {arch}\nMaintainer: Gente del Condado <headscale-gateway@gentedelcondado.es>\nDepends: python3, systemd, xdg-utils\nSection: net\nPriority: optional\nHomepage: https://gente-del-condado.github.io/headscale_gateway_ynh/\nDescription: Gateway HTTPS privado instalado como servicio con panel web\n Incluye motor Go, nodo VPN, proxy, DNS, certificados y copias cifradas.\n Crea un acceso al panel local en el menu de aplicaciones; configura la cuenta inicial antes de habilitar el servicio.\n')
            for name,body in [('preinst',PRE),('postinst',POST),('prerm',REMOVE),('postrm',"#!/bin/sh\nset -eu\nif [ -d /run/systemd/system ]; then systemctl daemon-reload; fi\n")]:
                p=control/name;p.write_text(body);p.chmod(0o755)
            target=output/f'headscale-gateway_{version}-1_{arch}.deb'
            if target.exists():raise ValueError('No se reemplaza un paquete existente')
            subprocess.run(['dpkg-deb','--root-owner-group','-Zgzip','--build',str(root),str(target)],check=True)
        else:
            rpmarch={'amd64':'x86_64','arm64':'aarch64'}[arch]
            top=base/'rpmbuild'
            for d in ['BUILD','RPMS','SOURCES','SPECS','SRPMS','BUILDROOT']:(top/d).mkdir(parents=True)
            spec=top/'SPECS/headscale-gateway.spec'
            epoch=int(os.environ.get('SOURCE_DATE_EPOCH') or subprocess.check_output(['git','-C',str(ROOT),'log','-1','--format=%ct','--','VERSION'],text=True).strip())
            date=datetime.datetime.fromtimestamp(epoch,datetime.timezone.utc).strftime('%a %b %d %Y')
            content=f'''Name: headscale-gateway
Version: {version}
Release: 1
Summary: Gateway HTTPS privado como servicio con panel web
License: AGPL-3.0-only
Vendor: Gente del Condado
Packager: Gente del Condado <headscale-gateway@gentedelcondado.es>
URL: https://gente-del-condado.github.io/headscale_gateway_ynh/
Requires: python3, systemd, xdg-utils
AutoReqProv: no
%description
Motor Go completo instalado como servicio, panel web, nodo VPN, proxy, DNS, certificados y copias cifradas. Acceso Headscale Gateway en el menú de aplicaciones.
%prep
%build
%install
mkdir -p %{{buildroot}}
cp -a {root}/. %{{buildroot}}/
%pre
{PRE.split('set -eu',1)[1]}
%post
{POST.split('set -eu',1)[1]}
%preun
{REMOVE.split('set -eu',1)[1]}
%postun
if [ -d /run/systemd/system ]; then systemctl daemon-reload; fi
%files
/usr/bin/headscale-gateway
%attr(0755,root,root) /usr/bin/headscale-gateway-configure
%attr(0755,root,root) /usr/bin/headscale-gateway-open-admin
/usr/share/applications/es.gentedelcondado.HeadscaleGateway.desktop
/usr/share/icons/hicolor/128x128/apps/es.gentedelcondado.HeadscaleGateway.png
/usr/libexec/headscale-gateway
/usr/lib/systemd/system/headscale-gateway.service
/usr/lib/sysusers.d/headscale-gateway.conf
/usr/lib/tmpfiles.d/headscale-gateway.conf
/usr/share/doc/headscale-gateway
/usr/share/licenses/headscale-gateway
%changelog
* {date} Gente del Condado <headscale-gateway@gentedelcondado.es> - {version}-1
- Motor compartido, servicio y acceso al panel local.
'''
            spec.write_text(content)
            subprocess.run(['rpmbuild','-bb','--target',rpmarch,'--define','_topdir '+str(top),'--define','__os_install_post %{nil}','--define','_build_id_links none','--define','debug_package %{nil}',str(spec)],check=True)
            artifacts=list((top/'RPMS').rglob('*.rpm'))
            if len(artifacts)!=1:raise ValueError('Se esperaba un paquete RPM')
            target=output/artifacts[0].name
            if target.exists():raise ValueError('No se reemplaza un paquete existente')
            shutil.copy2(artifacts[0],target)
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',required=True,type=Path);p.add_argument('--helper',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--arch',required=True,choices=['amd64','arm64']);p.add_argument('--format',required=True,choices=['deb','rpm'])
    a=p.parse_args();print(build(a.output,a.binary,a.helper,a.arch,a.format))
