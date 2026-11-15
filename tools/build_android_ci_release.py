#!/usr/bin/env python3
"""Construye los tres canales Android con una única compilación JNI y firma estable."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,urllib.request,zipfile
from pathlib import Path
from android_ci_signing import signing_profile,CERTIFICATE
from android_signing import load_environment
from check_android_artifact import verify
from publish_public_sources import snapshot
ROOT=Path(__file__).resolve().parents[1]
BUNDLETOOL_SHA='a099cfa1543f55593bc2ed16a70a7c67fe54b1747bb7301f37fdfd6d91028e29'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sdk=Path(os.environ['ANDROID_HOME']);ndk=sdk/'ndk/27.0.12077973';java=Path(os.environ['JAVA_HOME']);output=a.output.resolve()
    if output.exists() and any(output.iterdir()):raise ValueError('El destino debe estar vacío')
    output.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ);env.pop('HGW_ANDROID_SIGNING_BUNDLE',None)
    def run(args,environment=env):subprocess.run([str(x) for x in args],cwd=ROOT,env=environment,check=True)
    run([sys.executable,ROOT/'tools/build_android_apk.py','--release','--prepare-only','--sdk',sdk,'--ndk',ndk,'--java-home',java,'--gradle',ROOT/'android/gradlew'])
    def gradle(channel,*tasks,environment=env):run([ROOT/'android/gradlew','--no-daemon','--max-workers=2','-p',ROOT/'android','-PreleaseChannel='+channel,*tasks],environment)
    def artifact(directory,pattern,name):
        files=list((ROOT/directory).glob(pattern))
        if len(files)!=1:raise ValueError('No se ha encontrado un único artefacto Android')
        destination=output/name;shutil.copy2(files[0],destination);return destination
    gradle('fdroid',':assembleRelease')
    unsigned=artifact('android/build/outputs/apk/release','*-unsigned.apk','headscale-gateway-fdroid-unsigned.apk')
    verify(unsigned,sdk,ndk,java,['arm64-v8a','x86_64'],True,True,None)
    with signing_profile() as config:
        signed_env=dict(env,**load_environment(config))
        # Evita conservar el APK anterior al cambiar de canal incrementalmente.
        for file in (ROOT/'android/build/outputs/apk/release').glob('*.apk'):file.unlink()
        gradle('direct',':assembleRelease',':bundleRelease',':lintRelease',environment=signed_env)
        apk=artifact('android/build/outputs/apk/release','*.apk','headscale-gateway-release.apk')
        info=verify(apk,sdk,ndk,java,['arm64-v8a','x86_64'],True,False,None)
        if info['certificate_sha256']!=CERTIFICATE:raise ValueError('La APK no conserva la firma publicada')
        aab=artifact('android/build/outputs/bundle/release','*.aab','headscale-gateway-play.aab')
        with tempfile.TemporaryDirectory(prefix='hgw-bundletool-') as temporary:
            jar=Path(temporary)/'bundletool.jar'
            with urllib.request.urlopen('https://github.com/google/bundletool/releases/download/1.18.3/bundletool-all-1.18.3.jar',timeout=60) as response,jar.open('wb') as f:shutil.copyfileobj(response,f)
            if hashlib.sha256(jar.read_bytes()).hexdigest()!=BUNDLETOOL_SHA:raise ValueError('Bundletool no coincide con la herramienta fijada')
            bundle=verify(aab,sdk,ndk,java,['arm64-v8a','x86_64'],True,False,jar)
            if bundle['certificate_sha256']!=CERTIFICATE:raise ValueError('El AAB no conserva la firma publicada')
    # La instantánea no incluye historial, credenciales, cachés ni compilados.
    version=(ROOT/'VERSION').read_text().strip()
    with tempfile.TemporaryDirectory(prefix='hgw-android-source-') as temporary:
        source=Path(temporary);snapshot(source)
        with zipfile.ZipFile(output/f'headscale-gateway-android-sources-{version}.zip','w',zipfile.ZIP_DEFLATED) as z:
            for file in sorted(source.rglob('*')):
                if file.is_file():z.write(file,file.relative_to(source).as_posix())
    (output/'ANDROID-VALIDATION.json').write_text(json.dumps({'version':version,'certificate_sha256':CERTIFICATE,'apk':'verified','aab':'verified; Play Store prepared only','fdroid':'unsigned; not submitted','device_upgrade':'Not executed by this build; signature, package and version are checked'},indent=2)+'\n')
    checks=[]
    for file in sorted(output.iterdir()):
        with file.open('rb') as stream:checks.append(hashlib.file_digest(stream,'sha256').hexdigest()+'  '+file.name)
    (output/'SHA256SUMS').write_text('\n'.join(checks)+'\n')
    print('ANDROID_RELEASE_OK: firma estable, ambas arquitecturas y tres canales verificados; ninguna tienda publicada')

if __name__=='__main__':main()
