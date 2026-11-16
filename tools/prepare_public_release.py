#!/usr/bin/env python3
"""Prepara descargas públicas verificadas sin exportar el historial privado."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

from desktop_compliance import verify as verify_complete
from package_release import write_archive
from publish_public_sources import snapshot
import desktop_sources
from package_linux import build as build_linux
from prepare_flatpak import prepare as prepare_flatpak

ROOT=Path(__file__).resolve().parents[1]
SOURCE_REPOSITORY='Gente-del-Condado/headscale_gateway'
PUBLIC_REPOSITORY='Gente-del-Condado/headscale_gateway_releases'


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def safe_extract(archive,destination):
    """Solo archivos y directorios del paquete; nunca enlaces o rutas externas."""
    destination=Path(destination)
    if isinstance(archive,zipfile.ZipFile):
        for info in archive.infolist():
            name=PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts or ((info.external_attr>>16)&0o170000)==0o120000:
                raise ValueError('Ruta o enlace no permitido en ZIP')
        archive.extractall(destination)
    else:
        members=archive.getmembers()
        if any(PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts or not(m.isfile() or m.isdir()) for m in members):
            raise ValueError('Ruta o enlace no permitido en TAR')
        archive.extractall(destination,filter='data')


def detach_sources(runtime,platform,output,base_url=None):
    runtime,output=Path(runtime),Path(output)
    manifest=verify_complete(runtime,platform)
    shared = desktop_sources.prepare(runtime/'legal/sources', manifest['lock'], output/'desktop-sources')
    records = shared['sources']
    # Solo cambia el árbol de trabajo extraído: los originales ya publicados no se tocan.
    shutil.rmtree(runtime/'legal/sources')
    (runtime/'legal/PUBLIC-SOURCES.json').write_text(json.dumps({'release':shared['release'], 'sources':records},indent=2)+'\n')
    (runtime/'legal/README.md').write_text('''# Fuentes correspondientes y avisos

Este paquete ligero conserva todos los avisos y los fuentes del cliente propio.
Los fuentes completos de Electron, Chromium (incluido FFmpeg), Node y NAN se
publican en una release reutilizable de dependencias. PUBLIC-SOURCES.json contiene
sus versiones, enlaces públicos y SHA-256 exactos. Solo Chromium requiere unir
sus partes en orden. Los fuentes son comunes a Linux y Windows y no se duplican.

Este software usa bibliotecas FFmpeg bajo LGPL-2.1-or-later. Conserva sus avisos,
fuentes exactos, parches e instrucciones de compilación al redistribuirlo. Puedes
sustituir libffmpeg.so o ffmpeg.dll por una compilación de ABI compatible. No se
restringe la ingeniería inversa para depurar esas modificaciones.

Las instrucciones de reconstrucción de Electron y FFmpeg están en
application-source/packaging/desktop/README.md. Las revisiones fijadas son las
mismas que las del paquete original; no se modifican los binarios del runtime.
''')
    legal_files={p.relative_to(runtime/'legal').as_posix():digest(p) for p in (runtime/'legal').rglob('*') if p.is_file() and p.name!='manifest.json'}
    detached=dict(manifest,format=2,legal_files=legal_files,external_sources=records)
    (runtime/'legal/manifest.json').write_text(json.dumps(detached,indent=2,sort_keys=True)+'\n')
    expected=dict(manifest['runtime_files']);expected.update({'legal/'+n:v for n,v in legal_files.items()});expected['legal/manifest.json']=digest(runtime/'legal/manifest.json')
    actual={p.relative_to(runtime).as_posix():digest(p) for p in runtime.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('La separación ha alterado el runtime o los avisos')
    return detached


def prepare(output):
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('El destino debe estar vacío')
    output.mkdir(parents=True,exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip()
    import re
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Versión estable no válida')
    metadata=json.loads(subprocess.check_output(['gh','api',f'repos/{SOURCE_REPOSITORY}/releases/tags/v{version}']))
    if metadata['draft'] or metadata['prerelease']:raise ValueError('La entrega privada no está publicada')
    assets={a['name']:a for a in metadata['assets']}
    def download(name,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        subprocess.run(['gh','release','download','v'+version,'--repo',SOURCE_REPOSITORY,'--pattern',name,'--dir',str(folder)],check=True)
        p=folder/name
        if p.stat().st_size!=assets[name]['size'] or 'sha256:'+digest(p)!=assets[name]['digest']:raise ValueError('Descarga privada alterada: '+name)
        return p
    base_url=f'https://github.com/{PUBLIC_REPOSITORY}/releases/download/v{version}/'
    with tempfile.TemporaryDirectory(prefix='hgw-public-prepare-') as temporary:
        temp=Path(temporary)
        for platform,archive_name in [('linux','gateway-tray-linux-x64.tar.gz'),('win32','gateway-tray-windows-x64.zip')]:
            inputs=temp/platform;inputs.mkdir()
            part_names=sorted(n for n in assets if n.startswith(archive_name+'.part-'))
            if not part_names:raise ValueError('No hay fragmentos del escritorio')
            combined=inputs/archive_name
            with combined.open('wb') as incoming:
                for name in part_names:
                    part=download(name,inputs)
                    with part.open('rb') as src:shutil.copyfileobj(src,incoming)
                    part.unlink()
            report=download('release-desktop-'+platform+'-parts.json',inputs)
            if digest(combined)!=json.loads(report.read_text())['sha256']:raise ValueError('El escritorio reconstruido no coincide')
            extract=inputs/'extracted'
            if platform=='linux':
                with tarfile.open(combined,'r:gz') as a:safe_extract(a,extract)
            else:
                with zipfile.ZipFile(combined) as a:safe_extract(a,extract)
            combined.unlink()
            runtime=extract/'Gateway-Tray'
            detach_sources(runtime,platform,output,base_url)
            name='gateway-tray-'+('linux-x64.tar.gz' if platform=='linux' else 'windows-x64.zip')
            pairs=[(p,'Gateway-Tray/'+p.relative_to(runtime).as_posix()) for p in sorted(runtime.rglob('*')) if p.is_file()]
            write_archive(output/name,pairs,windows=platform=='win32')
            shutil.rmtree(inputs)
        for name in sorted(assets):
            if name.startswith('gateway-tray-') or name.startswith('release-desktop-') or name in ('headscale-gateway-fuentes.zip','SHA256SUMS','ANDROID-SHA256SUMS'):continue
            download(name,output)
        for arch in ['amd64','arm64']:
            archive=output/f'headscale-gateway-linux-{arch}.tar.gz'
            binaries=temp/('engine-'+arch)
            with tarfile.open(archive,'r:gz') as a:
                wanted=[m for m in a if m.name in ('headscale-gateway','hgw-ca-helper')]
                if len(wanted)!=2:raise ValueError('Faltan motor y helper')
                for m in wanted:a.extract(m,binaries,filter='data')
            for kind in ['deb','rpm']:build_linux(output,binaries/'headscale-gateway',binaries/'hgw-ca-helper',arch,kind)
        public_sources=temp/'public-sources';snapshot(public_sources)
        source_zip=output/f'headscale-gateway-fuentes-publicos-{version}.zip'
        with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(public_sources.rglob('*')):
                if p.is_file():z.write(p,'headscale-gateway/'+p.relative_to(public_sources).as_posix())
        shutil.copy2(ROOT/'yunohost/payload/source.tar.gz',output/f'headscale-gateway-go-sources-{version}.tar.gz')
        prepare_flatpak(output/'flatpak-source')
        for parts_folder in list(output.glob('*.parts')):
            for p in parts_folder.glob('*.part-*'):shutil.move(p,output/p.name)
            shutil.rmtree(parts_folder)
    sums=[]
    for p in sorted(output.iterdir()):
        if p.is_file():sums.append(digest(p)+'  '+p.name)
    (output/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
    print(json.dumps({'version':version,'files':len(sums)+1,'output':str(output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.output)
