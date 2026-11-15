#!/usr/bin/env python3
"""Detecta releases estables de Forgejo; solo despacha compilaciones aprobadas."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='Gente-del-Condado/headscale_gateway'
FORGEJO_API='https://gentedelcondado.es/forgejo/api/v1/repos/wolfbelmi88/headscale_gateway'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Nunca reenviar el Bearer al portal SSO ni a otro origen.
    def redirect_request(self,*args,**kwargs):return None


def github(path,missing=False):
    r=subprocess.run(['gh','api','repos/'+REPOSITORY+'/'+path],capture_output=True,text=True)
    if r.returncode:
        if missing and 'HTTP 404' in r.stderr:return None
        raise ValueError('No se pudo consultar GitHub')
    return json.loads(r.stdout)


def forgejo(path,missing=False):
    token=os.environ.get('FORGEJO_RELEASE_READ_TOKEN','')
    if not token:raise ValueError('Falta FORGEJO_RELEASE_READ_TOKEN en GitHub Actions')
    req=urllib.request.Request(FORGEJO_API+path,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
            if 'application/json' not in response.headers.get('Content-Type',''):raise ValueError('Forgejo no devuelve JSON: revisar el SSO')
            body=response.read(2**20+1)
            if len(body)>2**20:raise ValueError('Respuesta de Forgejo demasiado grande')
            return json.loads(body)
    except urllib.error.HTTPError as error:
        if missing and error.code==404:return None
        raise ValueError('Forgejo no permite la lectura de la API (HTTP '+str(error.code)+'); revisar token y SSO') from None
    except urllib.error.URLError:
        raise ValueError('No se puede conectar a la API de Forgejo') from None


def tag_commit(tag):
    obj=github('git/ref/tags/'+tag,missing=True)
    if not obj:return None
    obj=obj['object']
    for _ in range(5):
        if obj['type']=='commit':return obj['sha']
        if obj['type']!='tag':raise ValueError('La etiqueta no apunta a un commit')
        obj=github('git/tags/'+obj['sha'])['object']
    raise ValueError('Demasiadas etiquetas anidadas')


def decision(version,head,tag_sha,release,quality,published,busy=False,origin_sha=None):
    """Una etiqueta sola, un borrador o una CI de otro SHA nunca autorizan publicar."""
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Versión estable no válida')
    if published:return False,'La versión ya está publicada; se conservan sus archivos'
    if not release:return False,'Todavía no existe una release de Forgejo para VERSION'
    if release.get('draft') or release.get('prerelease') or release.get('tag_name')!='v'+version:
        return False,'Forgejo todavía no ha publicado esta versión estable'
    if tag_sha!=head or origin_sha!=head:return False,'Las etiquetas de Forgejo/GitHub y main no coinciden; se espera al espejo'
    if not quality:return False,'Falta calidad correcta de main para este mismo SHA'
    if busy:return False,'Ya hay una compilación de esta revisión en curso'
    return True,'Release de Forgejo, etiqueta, main y calidad comprobados'


def inspect(expected_sha=None):
    if os.environ.get('GITHUB_REPOSITORY',REPOSITORY)!=REPOSITORY:raise ValueError('Repositorio de origen no autorizado')
    version=(ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Versión estable no válida')
    head=github('commits/main')['sha']
    local=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if local!=head or (expected_sha and head!=expected_sha):raise ValueError('La revisión ya no es main; no se publica')
    # Comprueba también autenticación y SSO aunque la versión esté ya distribuida.
    repository=forgejo('')
    if repository.get('full_name')!='wolfbelmi88/headscale_gateway' or not repository.get('private'):
        raise ValueError('Forgejo no devuelve el principal privado esperado')
    published=github('releases/tags/v'+version,missing=True)
    if published and (published['draft'] or published['prerelease']):published=None
    # Una versión nueva debe avanzar también respecto de las entregas existentes.
    previous=github('releases?per_page=100')
    stable=[tuple(map(int,r['tag_name'][1:].split('.'))) for r in previous if not r['draft'] and not r['prerelease'] and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',r['tag_name'])]
    if stable and tuple(map(int,version.split('.'))) < max(stable):raise ValueError('VERSION retrocede respecto de una entrega estable; no se publica')
    release=forgejo('/releases/tags/v'+version,missing=True)
    tag_sha=tag_commit('v'+version)
    origin_tag=forgejo('/tags/v'+version,missing=True)
    origin_sha=origin_tag['commit']['sha'] if origin_tag else None
    runs=github('actions/runs?head_sha='+head+'&per_page=100')['workflow_runs']
    quality=any(r['path']=='.github/workflows/quality.yml' and r['head_branch']=='main' and r['event']=='push' and r['conclusion']=='success' for r in runs)
    busy=any(r['path'] in ('.github/workflows/release-build.yml','.github/workflows/release-draft.yml') and r['status']!='completed' and str(r['id'])!=os.environ.get('GITHUB_RUN_ID') for r in runs)
    ready,reason=decision(version,head,tag_sha,release,quality,bool(published),busy,origin_sha)
    return {'ready':ready,'reason':reason,'version':version,'sha':head,'forgejo_api':'authenticated JSON OK','tag_sha':tag_sha,'forgejo_tag_sha':origin_sha,'quality':quality}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dispatch',action='store_true');p.add_argument('--expected-sha');p.add_argument('--probe',action='store_true');a=p.parse_args()
    try:
        if a.probe:
            repository=forgejo('')
            if repository.get('full_name')!='wolfbelmi88/headscale_gateway' or not repository.get('private'):raise ValueError('Principal privado inesperado')
            releases=forgejo('/releases?limit=1')
            if not isinstance(releases,list):raise ValueError('Respuesta de releases no válida')
            version=(ROOT/'VERSION').read_text().strip()
            if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Versión estable no válida')
            tag=forgejo('/tags/v'+version,missing=True)
            if tag and not re.fullmatch(r'[0-9a-f]{40}',tag['commit']['sha']):raise ValueError('Etiqueta Forgejo no válida')
            print('FORGEJO_API_OK: repositorio, releases, etiquetas, token de lectura y SSO comprobados; ninguna escritura')
            return
        result=inspect(a.expected_sha)
        print(json.dumps(result,ensure_ascii=False))
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as out:
                out.write('ready='+str(result['ready']).lower()+'\n')
        if a.dispatch and result['ready']:
            # workflow_dispatch sí puede iniciar otra ejecución con GITHUB_TOKEN.
            # La release creada con ese token no se usa como disparador implícito.
            subprocess.run(['gh','workflow','run','release-build.yml','--repo',REPOSITORY,'--ref','main','-f','expected_sha='+result['sha']],check=True)
        if a.expected_sha and not result['ready']:raise ValueError(result['reason'])
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        p.exit(1,str(error)+'\n')

if __name__=='__main__':main()
