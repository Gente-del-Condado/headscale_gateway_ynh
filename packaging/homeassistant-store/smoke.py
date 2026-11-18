#!/usr/bin/env python3
"""Pruebas nativas en contenedores desechables; no utiliza una instalación real."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

HERE = Path(__file__).resolve().parent


def run(*arguments, capture=False, input=None):
    return subprocess.run([str(a) for a in arguments], check=True, text=True, input=input,
                          stdout=subprocess.PIPE if capture else None).stdout


def main(app, image, version):
    label = 'ha-image-test-' + uuid.uuid4().hex[:10]
    network, server = label + '-net', label + '-server'
    with tempfile.TemporaryDirectory(prefix='ha-image-test-') as temporary:
        root = Path(temporary)
        try:
            if app == 'jacksignal_installer':
                config = root / 'homeassistant'
                config.mkdir()
                (config / 'configuration.yaml').write_text('homeassistant: {}\n')
                (config / 'user-audio.wav').write_bytes(b'fixture-user-audio')
                old = config / 'custom_components/jacksignal'
                old.mkdir(parents=True)
                (old / 'manifest.json').write_text(json.dumps({'domain':'jacksignal','version':'0.0.0'}))
                for _ in range(2):
                    run('docker', 'run', '--rm', '--network', 'none', '-v', str(config) + ':/homeassistant', image)
                assert json.loads((old / 'manifest.json').read_text())['version'] == version
                assert json.loads((config / '.jacksignal-previous/manifest.json').read_text())['version'] == '0.0.0'
                assert (config / 'user-audio.wav').read_bytes() == b'fixture-user-audio'
                print('JACKSIGNAL_OK: instalación, repetición, copia anterior y datos conservados')
                return
            run('docker', 'network', 'create', '--internal', '--subnet', '172.30.32.0/24', network)
            if app == 'headscale_gateway':
                run('docker', 'run', '--rm', '--network', network, '--ip', '172.30.32.2',
                    '--add-host', 'supervisor:127.0.0.1', '--entrypoint', 'python3',
                    '-v', str(HERE / 'check_gateway.py') + ':/check_gateway.py:ro',
                    '-v', str(Path(app).resolve() / 'config.yaml') + ':/addon-config.yaml:ro', image, '/check_gateway.py')
                return
            if app == 'pivigia':
                data = root / 'data'
                data.mkdir()
                (data / 'options.json').write_text(json.dumps({'admin_token':'isolated-container-test-token-000', 'panel_login':'both'}))
                run('docker', 'run', '-d', '--name', server, '--network', network, '--ip', '172.30.32.10',
                    '-v', str(data) + ':/data', image)
                check = '''import json,time,urllib.request,urllib.error,cv2,numpy as np
base='http://127.0.0.1:8099'
for _ in range(100):
 try:
  if urllib.request.urlopen(base+'/healthz',timeout=2).status==200:break
 except OSError:time.sleep(.2)
else:raise AssertionError('PiVigia no arranca')
request=urllib.request.Request(base+'/api/status',headers={'Authorization':'Bearer isolated-container-test-token-000'})
status=json.load(urllib.request.urlopen(request,timeout=5))
assert status['version']==VERSION and status['model_ready'] and status['worker_alive'],status
net=cv2.dnn.readNetFromCaffe('/opt/pivigia/models/deploy.prototxt','/opt/pivigia/models/mobilenet.caffemodel')
net.setInput(cv2.dnn.blobFromImage(np.zeros((300,300,3),dtype=np.uint8),0.007843,(300,300),127.5))
assert net.forward().shape[-1]==7
try:urllib.request.urlopen(base+'/api/status',timeout=5)
except urllib.error.HTTPError as e:assert e.code in (401,403)
else:raise AssertionError('El estado privado admite tráfico sin autenticar')
print('PIVIGIA_OK: arranque, token, trabajador y ejecución real del modelo OpenCV')
'''
                run('docker', 'exec', '-i', server, 'python', '-c', 'VERSION=' + repr(version) + '\n' + check)
            elif app == 'private_git_manager':
                run('docker', 'run', '-d', '--name', server, '--network', network, '--ip', '172.30.32.10', image)
                check = '''import json,time,urllib.request,urllib.error
base='http://172.30.32.10:8099/'
for _ in range(100):
 try:
  if urllib.request.urlopen(base+'health',timeout=2).status==200:break
 except OSError:time.sleep(.2)
else:raise AssertionError('El gestor no arranca')
def request(path,method='GET',payload=None):
 data=json.dumps(payload).encode() if payload is not None else None
 r=urllib.request.Request(base+path,data=data,method=method,headers={'X-PGM-Request':'1','Content-Type':'application/json'})
 return urllib.request.urlopen(r,timeout=10).read()
assert json.loads(request('api/state'))['version']==VERSION
assert b'static/app.js' in request('')
key=json.loads(request('api/keys','POST',{'name':'Isolated container smoke test'}))
assert key['public'].startswith('ssh-ed25519 ')
repo=json.loads(request('api/repos','POST',{'name':'fixture','url':'https://example.org/owner/repo.git','ref':'main','token':'smoke-only-token'}))
assert b'smoke-only-token' not in request('api/state')
request('api/repos/'+repo['id'],'DELETE');request('api/keys/'+key['id'],'DELETE')
print('PGM_OK: Ingress, versión, interfaz, claves y ocultación de credenciales')
'''
                run('docker', 'run', '--rm', '--network', network, '--ip', '172.30.32.2',
                    '--entrypoint', 'python', image, '-c', 'VERSION=' + repr(version) + '\n' + check)
                deny = '''import urllib.request,urllib.error
r=urllib.request.Request('http://172.30.32.10:8099/api/state',headers={'X-Forwarded-For':'172.30.32.2'})
try:urllib.request.urlopen(r,timeout=5)
except urllib.error.HTTPError as e:assert e.code==403
else:raise AssertionError('Una cabecera permite suplantar Ingress')
print('PGM_OK: rechazo de acceso y suplantación fuera de Ingress')'''
                run('docker', 'run', '--rm', '--network', network, '--ip', '172.30.32.4', '--entrypoint', 'python', image, '-c', deny)
            else:
                raise ValueError('Aplicación sin prueba de contenedor')
        finally:
            subprocess.run(['docker', 'logs', '--tail', '50', server], check=False)
            subprocess.run(['docker', 'rm', '-f', server], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['docker', 'network', 'rm', network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # El contenedor crea archivos como root. Devolver solo el directorio
            # temporal del ensayo al runner permite retirarlo sin omitir errores.
            run('docker', 'run', '--rm', '--network', 'none', '--user', '0',
                '--entrypoint', 'chown', '-v', str(root) + ':/lab', image,
                '-R', str(os.getuid()) + ':' + str(os.getgid()), '/lab')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    main(args.app, args.image, args.version)
