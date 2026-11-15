#!/usr/bin/env python3
"""Genera el árbol público Flatpak con avisos exactos, sin código ni datos privados."""
from pathlib import Path
import argparse
import shutil
import hashlib
import subprocess
from package_platforms import add_notices
ROOT=Path(__file__).resolve().parents[1]

def prepare(destination):
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('El destino debe estar vacío')
    shutil.copytree(ROOT/'packaging/flatpak',destination,dirs_exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip()
    date=subprocess.check_output(['git','-C',str(ROOT),'log','-1','--format=%cs','--','VERSION'],text=True).strip()
    values={'VERSION':version,'DATE':date}
    for key,arch in [('AMD64_SHA256','amd64'),('ARM64_SHA256','arm64')]:
        with (ROOT/'yunohost/payload'/('headscale-gateway-linux-'+arch)).open('rb') as f:values[key]=hashlib.file_digest(f,'sha256').hexdigest()
    for path in list(destination.rglob('*.in')):
        text=path.read_text()
        for key,value in values.items():text=text.replace('@'+key+'@',value)
        path.with_suffix('').write_text(text);path.unlink()
    for name in ['LICENSE','NOTICE']:shutil.copy2(ROOT/name,destination/'files'/name)
    (destination/'README.md').write_text((destination/'README.md').read_text().replace('1.4.8',version))
    add_notices(destination/'files/notices')
    return destination

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);a=p.parse_args();print(prepare(a.destination))
