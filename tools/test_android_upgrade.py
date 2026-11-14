#!/usr/bin/env python3
"""Construye únicamente la instrumentación firmada; nunca se incorpora a la APK."""
from pathlib import Path
import argparse,os,subprocess,sys,zipfile
from android_signing import load_environment
parser=argparse.ArgumentParser(description='Construye una sonda separada para actualizar la APK directa 1.4.7 en una instalación de laboratorio vacía; no instala nada.')
parser.add_argument('--sdk',type=Path,required=True)
parser.add_argument('--java-home',type=Path,required=True)
parser.add_argument('--signing-config',type=Path,required=True)
parser.add_argument('--output',type=Path,default=Path('builds/android-upgrade-probe'))
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]; stage=args.output.resolve(); stage.mkdir(parents=True,exist_ok=True)
sdk=args.sdk.resolve(); bt=sdk/'build-tools/36.0.0'; jar=sdk/'platforms/android-36/android.jar'; jdk=args.java_home.resolve()
env=dict(os.environ,JAVA_HOME=str(jdk),**load_environment(args.signing_config))
manifest=stage/'AndroidManifest.xml';manifest.write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="org.headscalegateway.upgradetest"><uses-sdk android:minSdkVersion="26" android:targetSdkVersion="36"/><application android:label="HGW Upgrade Probe" android:allowBackup="false"/><instrumentation android:name="org.headscalegateway.upgradetest.UpgradeProbe" android:targetPackage="org.headscalegateway.android"/></manifest>''')
def run(args):subprocess.run([str(x) for x in args],check=True,env=env)
classes=stage/'classes';classes.mkdir(exist_ok=True)
run([jdk/'bin/javac','-source','8','-target','8','-classpath',jar,'-d',classes,root/'android/src/upgradeTest/java/org/headscalegateway/upgradetest/UpgradeProbe.java'])
run([jdk/'bin/jar','cf',stage/'classes.jar','-C',classes,'.'])
run([bt/'d8','--lib',jar,'--min-api','26','--output',stage,stage/'classes.jar'])
run([bt/'aapt','package','-f','-M',manifest,'-I',jar,'-F',stage/'unsigned.apk'])
with zipfile.ZipFile(stage/'unsigned.apk','a') as z:z.write(stage/'classes.dex','classes.dex')
run([bt/'zipalign','-f','4',stage/'unsigned.apk',stage/'aligned.apk'])
run([bt/'apksigner','sign','--ks',env['HGW_ANDROID_KEYSTORE'],'--ks-key-alias',env['HGW_ANDROID_KEY_ALIAS'],'--ks-pass','env:HGW_ANDROID_STORE_PASSWORD','--key-pass','env:HGW_ANDROID_KEY_PASSWORD','--out',stage/'probe.apk',stage/'aligned.apk'])
print('Sonda separada firmada sin exponer credenciales')
