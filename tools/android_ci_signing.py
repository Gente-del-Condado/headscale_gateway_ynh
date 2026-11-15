#!/usr/bin/env python3
"""Valida la identidad Android existente sin registrar ni exportar la clave."""
import argparse,base64,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
from contextlib import contextmanager

CERTIFICATE='5a75142e4dc97345603c812d87d1e69ec7bcb2947e714fbb8e3977c16adf684f'

@contextmanager
def signing_profile():
    raw=os.environ.get('HGW_ANDROID_SIGNING_BUNDLE','')
    if not raw:raise ValueError('Falta ANDROID_SIGNING_BUNDLE en GitHub Actions')
    try:
        b=json.loads(raw)
        if b.get('format')!=1 or b.get('certificate_sha256')!=CERTIFICATE or not re.fullmatch(r'[A-Za-z0-9_-]{32,200}',b.get('password','')) or b.get('alias')!='headscale-gateway':raise ValueError()
        key=base64.b64decode(b['keystore_base64'],validate=True)
        if not 1000<len(key)<30000:raise ValueError()
    except (ValueError,KeyError,TypeError):raise ValueError('El secreto de firma no tiene el formato o identidad esperados') from None
    if os.environ.get('GITHUB_ACTIONS')=='true':
        # GitHub conoce el JSON completo como secreto, pero no sus valores derivados.
        print('::add-mask::'+b['password'],flush=True)
        print('::add-mask::'+b['keystore_base64'],flush=True)
    with tempfile.TemporaryDirectory(prefix='hgw-android-signing-',dir=os.environ.get('RUNNER_TEMP')) as temporary:
        root=Path(temporary);root.chmod(0o700)
        for name,content in [('release.p12',key),('release.password',b['password'].encode()),('signing.json',json.dumps({'format':1,'keystore':'release.p12','password_file':'release.password','alias':b['alias']}).encode())]:
            p=root/name;p.touch(mode=0o600);p.write_bytes(content)
        # keytool recibe únicamente la ruta privada a la contraseña, nunca su valor.
        certificate=subprocess.run(['keytool','-exportcert','-alias',b['alias'],'-keystore',str(root/'release.p12'),'-storepass:file',str(root/'release.password')],capture_output=True,check=False)
        if certificate.returncode or hashlib.sha256(certificate.stdout).hexdigest()!=CERTIFICATE:raise ValueError('La clave Android no coincide con la firma publicada')
        yield root/'signing.json'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true',required=True);a=p.parse_args()
    try:
        with signing_profile():print('FIRMA_ESTABLE_OK: certificado existente y clave verificables; nada publicado')
    except (ValueError,OSError):p.exit(1,'No se pudo verificar ANDROID_SIGNING_BUNDLE; revisa el secreto sin mostrar su contenido\n')
