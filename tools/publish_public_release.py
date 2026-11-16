#!/usr/bin/env python3
"""Publica solo artefactos revisados en destinos públicos fijos de GitHub."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DESTINATIONS={'general':1458413359,'flatpak':1458413634,'yunohost':1454598547,'homeassistant':1453195379}


def gh(*args):return subprocess.check_output(['gh',*args],text=True)


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def public_repository(identity):
    data=json.loads(gh('api','repositories/'+str(identity)))
    if data['private'] or data['owner']['login']!='Gente-del-Condado':raise ValueError('El destino no es un repositorio público autorizado')
    return data['full_name']


def publish_files(repository,tag,files,notes,latest=None,reuse=False):
    expected={p.name:digest(p) for p in files}
    query=subprocess.run(['gh','api',f'repos/{repository}/releases/tags/{tag}'],capture_output=True,text=True)
    if query.returncode==0:release=json.loads(query.stdout)
    else:
        if 'HTTP 404' not in query.stderr:raise ValueError('No se pudo consultar la release pública')
        drafts=[r for r in json.loads(gh('api',f'repos/{repository}/releases?per_page=100')) if r['tag_name']==tag and r['draft']]
        if len(drafts)>1:raise ValueError('Hay varios borradores con esta etiqueta')
        if drafts:release=drafts[0]
        else:
            head=json.loads(gh('api',f'repos/{repository}/git/ref/heads/main'))['object']['sha']
            options=[] if latest is None else ['-f','make_latest='+str(latest).lower()]
            release=json.loads(gh('api',f'repos/{repository}/releases','--method','POST','-f','tag_name='+tag,'-f','target_commitish='+head,'-f','name=Headscale Gateway '+tag,'-f','body='+notes,'-F','draft=true',*options))
    if release['tag_name']!=tag or release['prerelease']:raise ValueError('La release no coincide con la entrega estable')
    actual={a['name']:a for a in release['assets']}
    if set(actual)-set(expected):raise ValueError('La release contiene archivos inesperados; no se modifica')
    for path in files:
        if path.name in actual:
            if actual[path.name].get('digest')!='sha256:'+expected[path.name]:raise ValueError('No se reemplaza un archivo diferente: '+path.name)
        elif release['draft']:gh('release','upload',tag,str(path),'--repo',repository)
        else:raise ValueError('La release publicada está incompleta; no se modifica')
    if release['draft']:
        # Todos los archivos se verifican autenticados antes de abrir el borrador.
        with tempfile.TemporaryDirectory(prefix='hgw-public-draft-check-') as temporary:
            for path in files:
                gh('release','download',tag,'--repo',repository,'--pattern',path.name,'--dir',temporary)
                downloaded=Path(temporary)/path.name
                if digest(downloaded)!=expected[path.name]:raise ValueError('Descarga de borrador incorrecta')
                downloaded.unlink()
        options=[] if latest is None else ['--latest='+str(latest).lower()]
        gh('release','edit',tag,'--repo',repository,'--draft=false',*options)
    if reuse and not release['draft']:
        # Un conjunto inmutable ya publicado se contrasta con los digest de GitHub.
        # La lectura anónima del índice y sumas confirma acceso sin repetir GB.
        for path in files:
            if path.name in ('DESKTOP-SOURCES.json', 'SHA256SUMS'):
                with urllib.request.urlopen(f'https://github.com/{repository}/releases/download/{tag}/{path.name}',timeout=60) as response:
                    if response.status!=200 or hashlib.file_digest(response,'sha256').hexdigest()!=expected[path.name]:
                        raise ValueError('Índice reutilizable no accesible o alterado')
        print('FUENTES_PUBLICADAS_REUTILIZADAS: '+tag,flush=True)
        return {'repository':repository,'tag':tag,'reused':True}
    records=[]
    for path in files:
        url=f'https://github.com/{repository}/releases/download/{tag}/{path.name}'
        # Sin tokens, cookies ni cabeceras de autenticación: debe descargar cualquier usuario.
        with urllib.request.urlopen(url,timeout=180) as response:
            value=hashlib.file_digest(response,'sha256').hexdigest()
            if response.status!=200 or value!=expected[path.name]:raise ValueError('Descarga anónima incorrecta: '+path.name)
        records.append({'name':path.name,'bytes':path.stat().st_size,'sha256':value,'anonymous_download':'OK','url':url})
        print('DESCARGA_PUBLICA_OK: '+repository+'/'+path.name,flush=True)
    return {'repository':repository,'tag':tag,'files':records}



def synchronize_public_tree(repository, source):
    """Actualiza un derivado sin copiar el historial del principal ni forzar referencias."""
    with tempfile.TemporaryDirectory(prefix='hgw-public-tree-') as temporary:
        clone=Path(temporary)/'repository'
        subprocess.run(['git','clone','--depth=1','https://github.com/'+repository+'.git',str(clone)],check=True)
        for path in clone.iterdir():
            if path.name=='.git':continue
            if path.is_dir() and not path.is_symlink():shutil.rmtree(path)
            else:path.unlink()
        shutil.copytree(source,clone,dirs_exist_ok=True)
        def git(*args):return subprocess.run(['git','-C',str(clone),*args],check=True)
        git('config','user.name','github-actions[bot]')
        git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
        git('add','--all')
        changed=subprocess.run(['git','-C',str(clone),'diff','--cached','--quiet']).returncode
        if changed:
            if changed!=1:raise ValueError('No se pudo revisar el árbol público')
            git('commit','-m','Actualizar distribución '+(ROOT/'VERSION').read_text().strip())
            git('push','origin','HEAD:main')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('installers',type=Path);p.add_argument('flatpak',type=Path);a=p.parse_args()
    version=(ROOT/'VERSION').read_text().strip()
    payload=a.installers.resolve();flatpak=a.flatpak.resolve()
    for line in (payload/'SHA256SUMS').read_text().splitlines():
        value,name=line.split(maxsplit=1)
        if Path(name).name!=name or digest(payload/name)!=value:raise ValueError('El artefacto preparado no coincide con su manifiesto')
    platforms={
        'yunohost':{f'headscale-gateway-yunohost-{version}.zip'},
        'homeassistant':{f'headscale-gateway-homeassistant-{version}.zip',f'headscale-gateway-hacs-{version}.zip'}}
    sources={f'headscale-gateway-go-sources-{version}.tar.gz',f'headscale-gateway-fuentes-publicos-{version}.zip'}
    from desktop_sources import gateway_files
    lock=json.loads((ROOT/'packaging/desktop/electron-sources.lock.json').read_text())
    general={p.name for p in gateway_files(payload,lock)}-set.union(*platforms.values())
    groups={'general':general,'yunohost':platforms['yunohost']|sources,'homeassistant':platforms['homeassistant']|sources,'flatpak':sources}
    # El helper recibe GH_TOKEN del entorno efímero; el token no se escribe en URLs.
    gh('auth','setup-git')
    with tempfile.TemporaryDirectory(prefix='hgw-public-readme-') as temporary:
        source=Path(temporary)
        shutil.copy2(ROOT/'packaging/releases/README.md',source/'README.md')
        for name in ['LICENSE','NOTICE']:shutil.copy2(ROOT/name,source/name)
        shutil.copy2(ROOT/'packaging/flatpak/files/es.gentedelcondado.HeadscaleGateway.png',source/'icon.png')
        synchronize_public_tree(public_repository(DESTINATIONS['general']),source)
    synchronize_public_tree(public_repository(DESTINATIONS['flatpak']),flatpak/'flatpak-source')
    reports=[]
    with tempfile.TemporaryDirectory(prefix='hgw-public-partition-') as temporary:
        base=Path(temporary)
        for group,names in groups.items():
            target=base/group;target.mkdir()
            for name in names:shutil.copy2(payload/name,target/name)
            if group=='flatpak':
                bundles=list(flatpak.glob('*.flatpak'))
                if not bundles:raise ValueError('No hay paquetes Flatpak comprobados')
                for bundle in bundles:shutil.copy2(bundle,target/bundle.name)
                with zipfile.ZipFile(target/f'headscale-gateway-flatpak-sources-{version}.zip','w',zipfile.ZIP_DEFLATED) as z:
                    for f in sorted((flatpak/'flatpak-source').rglob('*')):
                        if f.is_file() and '.git' not in f.parts:z.write(f,f.relative_to(flatpak/'flatpak-source').as_posix())
            files=sorted(target.iterdir())
            (target/'SHA256SUMS').write_text(''.join(digest(f)+'  '+f.name+'\n' for f in files))
            files=sorted(target.iterdir())
            repo=public_repository(DESTINATIONS[group])
            tag='v'+version+('-ynh1' if group=='yunohost' else '')
            notes=(f'Headscale Gateway {version}: distribución pública de {group}.\n\n'
                'El principal y su historial siguen privados. Los instaladores y fuentes correspondientes se distribuyen aquí sin autenticación.\n\n'
                'Gateway completo: paquetes del motor Go con panel web. Gateway-Tray es un cliente opcional y sus instaladores no requieren unir partes. '
                'Los fuentes de Electron/Chromium/FFmpeg se reutilizan desde la release de dependencias enlazada; solo Chromium usa partes. '
                'El software usa FFmpeg bajo LGPL-2.1-or-later; fuentes exactos, parches y avisos se enlazan desde cada instalador y esta release.\n\n'
                'Manuales: https://gente-del-condado.github.io/headscale_gateway_ynh/ y https://gente-del-condado.github.io/headscale_gateway_ha/.\n\n'
                'Android conserva la firma estable. El AAB de Play Store solo está preparado; no se envía a Play Store. '
                'Flatpak se distribuye directamente, sin solicitud ni aceptación en Flathub.\n')
            from desktop_sources import references
            dependencies=references(json.loads((ROOT/'packaging/desktop/electron-sources.lock.json').read_text()))
            notes+='Fuentes de Electron y dependencias: '+dependencies['release']+'\n\n'
            notes+='### Instaladores y fuentes de Gateway\n\n'
            for path in files:
                if path.name.endswith(('.zip','.tar.gz','.rpm','.deb','.flatpak','.apk','.aab')) or path.name=='SHA256SUMS':
                    notes+='- ['+path.name+'](https://github.com/'+repo+'/releases/download/'+tag+'/'+path.name+')\n'
            reports.append(publish_files(repo,tag,files,notes))
    (ROOT/'public-release-verification.json').write_text(json.dumps(reports,indent=2)+'\n')
    print('PUBLICACION_PUBLICA_OK: cuatro destinos y todas sus descargas anónimas verificadas')


if __name__=='__main__':main()
