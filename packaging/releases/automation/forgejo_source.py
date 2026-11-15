#!/usr/bin/env python3
"""Lee una release estable y sus fuentes sin exponer el historial del principal."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tarfile,tempfile,urllib.error,urllib.request
from pathlib import Path,PurePosixPath

OWNER='Gente-del-Condado'
REPOSITORY=OWNER+'/headscale_gateway_releases'
API='https://gentedelcondado.es/forgejo/api/v1/repos/wolfbelmi88/headscale_gateway'
DESTINATIONS={'general':'headscale_gateway_releases','flatpak':'headscale_gateway_flatpak','ynh':'headscale_gateway_ynh','ha':'headscale_gateway_ha'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def forgejo(path):
    token=os.environ.get('FORGEJO_RELEASE_READ_TOKEN','')
    if not token:raise ValueError('Falta FORGEJO_RELEASE_READ_TOKEN en el repositorio público')
    request=urllib.request.Request(API+path,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    try:return urllib.request.build_opener(NoRedirect).open(request,timeout=120)
    except urllib.error.HTTPError as error:raise ValueError('Forgejo no permite esta lectura (HTTP '+str(error.code)+'); revisar token y SSO') from None
    except urllib.error.URLError:raise ValueError('Forgejo no está disponible') from None


def forgejo_json(path):
    with forgejo(path) as response:
        if 'application/json' not in response.headers.get('Content-Type',''):raise ValueError('Forgejo no devuelve JSON; revisar el SSO')
        raw=response.read(2**20+1)
        if len(raw)>2**20:raise ValueError('Respuesta JSON demasiado grande')
        return json.loads(raw)


def github(path,missing=False):
    args=['gh','api','repos/'+OWNER+'/'+path]
    result=subprocess.run(args,capture_output=True,text=True)
    if result.returncode:
        if missing and 'HTTP 404' in result.stderr:return None
        raise ValueError('No se pudo consultar el estado público de GitHub')
    return json.loads(result.stdout)


def validate_release(release):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',release.get('tag_name','')) or release.get('draft') is not False or release.get('prerelease') is not False:
        raise ValueError('Solo se construyen releases estables publicadas')


def select_release():
    choices=[]
    for page in range(1,6):
        releases=forgejo_json('/releases?limit=50&page='+str(page))
        for release in releases:
            try:validate_release(release)
            except ValueError:continue
            choices.append(release)
        if len(releases)<50:break
    if not choices:return None
    return max(choices,key=lambda r:tuple(map(int,r['tag_name'][1:].split('.'))))


def completed(version,source_sha):
    general=github(DESTINATIONS['general']+'/releases/tags/v'+version,missing=True)
    if not general or general.get('draft'):return False
    marker='<!-- hgw-complete:'+source_sha+' -->'
    if marker not in (general.get('body') or ''):return False
    for name in ['flatpak','ynh','ha']:
        tag='v'+version+('-ynh1' if name=='ynh' else '')
        release=github(DESTINATIONS[name]+'/releases/tags/'+tag,missing=True)
        if not release or release.get('draft') or not release.get('assets'):return False
    return True


def plan():
    if os.environ.get('GITHUB_REPOSITORY',REPOSITORY)!=REPOSITORY:raise ValueError('Repositorio de control no autorizado')
    repository=forgejo_json('')
    if repository.get('full_name')!='wolfbelmi88/headscale_gateway' or not repository.get('private'):raise ValueError('No se está leyendo el principal privado esperado')
    release=select_release()
    if not release:return {'build':False,'reason':'No hay una release estable de Forgejo'}
    tag=forgejo_json('/tags/'+release['tag_name']);sha=tag['commit']['sha']
    if not re.fullmatch(r'[0-9a-f]{40}',sha):raise ValueError('Commit de origen no válido')
    version=release['tag_name'][1:]
    previous=github(DESTINATIONS['general']+'/releases?per_page=100')
    stable=[tuple(map(int,r['tag_name'][1:].split('.'))) for r in previous if not r['draft'] and not r['prerelease'] and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',r['tag_name'])]
    if stable and tuple(map(int,version.split('.')))<max(stable):return {'build':False,'reason':'No se retrocede a una versión antigua'}
    done=completed(version,sha)
    return {'build':not done,'version':version,'source_sha':sha,'tag':release['tag_name'],'reason':'Ya publicada y verificada' if done else 'Release estable de Forgejo autorizada'}


def extract_archive(archive,destination):
    """Exige una raíz única, archivos ordinarios y un tamaño total acotado."""
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('El destino debe estar vacío')
    members=archive.getmembers()
    if not members or len(members)>30000 or sum(m.size for m in members)>2**31:raise ValueError('Archivo de fuentes fuera de los límites')
    roots=set()
    for member in members:
        path=PurePosixPath(member.name)
        if not path.parts or path.is_absolute() or '..' in path.parts or '.git' in path.parts or '\\' in member.name or not(member.isfile() or member.isdir()):raise ValueError('Ruta o enlace no permitido en los fuentes')
        roots.add(path.parts[0])
    if len(roots)!=1:raise ValueError('El archivo no tiene una raíz única')
    destination.mkdir(parents=True,exist_ok=True)
    for member in members:
        parts=PurePosixPath(member.name).parts[1:]
        if not parts:continue
        target=destination.joinpath(*parts)
        if not target.resolve().is_relative_to(destination):raise ValueError('Ruta fuera del directorio de fuentes')
        if member.isdir():target.mkdir(parents=True,exist_ok=True)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as incoming,target.open('wb') as output:shutil.copyfileobj(incoming,output)
            target.chmod(0o755 if member.mode&0o111 else 0o644)
            os.utime(target,(member.mtime,member.mtime))


def verify_manifest(root):
    """Normaliza rutas de Windows; conserva las sumas originales de cada archivo."""
    root=Path(root)
    sys.path.insert(0,str(root/'tools'))
    from prepare_git_install import input_hashes,output_hashes
    manifest=json.loads((root/'git-install-manifest.json').read_text())
    def portable(values):return {name.replace('\\','/'):value for name,value in values.items()}
    if manifest.get('format')!=1 or not manifest.get('outputs'):
        raise ValueError('Manifiesto de instaladores no válido')
    if portable(output_hashes(root))!=manifest['outputs']:
        raise ValueError('Los instaladores extraídos no coinciden con el manifiesto')
    if portable(input_hashes(root))!=manifest['inputs'] or manifest['version']!=(root/'VERSION').read_text().strip():
        raise ValueError('Los instaladores no corresponden a los fuentes etiquetados')


def fetch(sha,version,destination,candidate_ref=None):
    if not re.fullmatch(r'[0-9a-f]{40}',sha) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Referencia no válida')
    if candidate_ref:
        if not re.fullmatch(r'codex/[a-z0-9-]+',candidate_ref):raise ValueError('La validación requiere una rama de revisión codex/')
        branches=forgejo_json('/branches?limit=100')
        branch=next((item for item in branches if item['name']==candidate_ref),None)
        if not branch or branch['commit']['id']!=sha:raise ValueError('La rama de revisión ha cambiado; se detiene la validación')
    else:
        release=forgejo_json('/releases/tags/v'+version);validate_release(release)
        tag=forgejo_json('/tags/v'+version)
        if tag['commit']['sha']!=sha:raise ValueError('La etiqueta ha cambiado; se detiene la construcción')
    with tempfile.TemporaryFile() as temporary:
        with forgejo('/archive/'+sha+'.tar.gz') as response:
            total=0
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>2**30:raise ValueError('Archivo comprimido demasiado grande')
                temporary.write(chunk)
        temporary.seek(0)
        with tarfile.open(fileobj=temporary,mode='r:gz') as archive:extract_archive(archive,destination)
    root=Path(destination).resolve()
    if (root/'VERSION').read_text().strip()!=version:raise ValueError('La versión etiquetada no coincide con VERSION')
    # Los publicadores usan git archive; este repositorio efímero tiene un único
    # commit de fuentes, sin padres ni historial privado. No se publica como espejo.
    timestamp=str(int((root/'VERSION').stat().st_mtime))+' +0000'
    environment=dict(os.environ,GIT_AUTHOR_DATE=timestamp,GIT_COMMITTER_DATE=timestamp)
    def git(*args):subprocess.run(['git','-C',str(root),*args],check=True,env=environment,stdout=subprocess.DEVNULL)
    git('init','-b','source');git('config','core.autocrlf','false');git('config','core.eol','lf');git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git('add','--all');git('commit','-m','Fuentes de '+sha)
    verify_manifest(root)
    print('FUENTES_FORGEJO_VERIFICADOS: '+version+' '+sha+'; sin historial privado')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',action='store_true');p.add_argument('--sha');p.add_argument('--version');p.add_argument('--destination',type=Path);p.add_argument('--candidate-ref');a=p.parse_args()
    try:
        if a.plan:
            result=plan();print(json.dumps(result,ensure_ascii=False))
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'],'a') as out:
                    for key,value in result.items():out.write(key+'='+str(value).lower()+'\n' if isinstance(value,bool) else key+'='+str(value)+'\n')
        elif a.sha and a.version and a.destination:fetch(a.sha,a.version,a.destination,a.candidate_ref)
        else:p.error('Usa --plan o --sha/--version/--destination')
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as error:p.exit(1,str(error)+'\n')

if __name__=='__main__':main()
