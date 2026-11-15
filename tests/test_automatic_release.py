"""Contratos de autorización y continuidad de la publicación automática."""
import hashlib,os,re,subprocess,sys,tempfile,textwrap,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import automatic_release as automatic
import android_ci_signing as signing

class AutomaticReleaseTest(unittest.TestCase):
    def decide(self,**changes):
        values=dict(version='1.4.9',head='a'*40,tag_sha='a'*40,release={'tag_name':'v1.4.9','draft':False,'prerelease':False},quality=True,published=False,busy=False,origin_sha='a'*40)
        values.update(changes);return automatic.decision(**values)[0]

    def test_only_published_forgejo_release_and_exact_approved_main_can_build(self):
        self.assertTrue(self.decide())
        for change in [dict(origin_sha='b'*40),dict(origin_sha=None),dict(tag_sha='b'*40),dict(quality=False),dict(published=True),dict(busy=True),dict(release=None),dict(release={'tag_name':'v1.4.9','draft':True}),dict(release={'tag_name':'v1.4.9','prerelease':True}),dict(release={'tag_name':'v1.4.8'})]:
            with self.subTest(change=change):self.assertFalse(self.decide(**change))

    def test_annotated_tags_resolve_to_commit_and_never_arbitrary_object(self):
        with patch.object(automatic,'github',side_effect=[{'object':{'type':'tag','sha':'tag-object'}},{'object':{'type':'commit','sha':'commit'}}]):self.assertEqual(automatic.tag_commit('v1.4.9'),'commit')
        with patch.object(automatic,'github',return_value={'object':{'type':'tree','sha':'tree'}}):
            with self.assertRaises(ValueError):automatic.tag_commit('v1.4.9')

    def test_sso_redirect_cannot_forward_bearer(self):
        self.assertIsNone(automatic.NoRedirect().redirect_request(None,None,302,'login',{},'https://example.invalid/login'))
        with patch.dict(os.environ,{'FORGEJO_RELEASE_READ_TOKEN':''}):
            with self.assertRaisesRegex(ValueError,'Falta FORGEJO'):automatic.forgejo('')

    def test_signing_rejects_missing_or_different_identity_without_logging_bundle(self):
        for value in ['', '{"format":1,"password":"fixture-private-value"}']:
            with patch.dict(os.environ,{'HGW_ANDROID_SIGNING_BUNDLE':value}):
                with self.assertRaises(ValueError) as error:
                    with signing.signing_profile():self.fail('No debe aceptar otra identidad')
                self.assertNotIn('fixture-private-value',str(error.exception))

    def test_release_assembly_includes_signed_android_and_rejects_corrupt_artifacts(self):
        workflow=(ROOT/'.github/workflows/release-draft.yml').read_text()
        blocks=re.findall(r"^          python3 - <<'PY'\n(.*?)^          PY$",workflow,re.M|re.S)
        assembly=next(textwrap.dedent(code) for code in blocks if "expected={'release-server'" in code)
        for corrupt in [False,True]:
            with self.subTest(corrupt=corrupt),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);(root/'tools').symlink_to(ROOT/'tools',target_is_directory=True)
                names={'release-server':'engine.tar.gz','release-desktop-linux':'tray.tar.gz','release-desktop-win32':'tray.zip','release-android':'headscale-gateway-release.apk'}
                for folder,name in names.items():
                    stage=root/'builds/release-download'/folder;stage.mkdir(parents=True)
                    payload=b'fixture-reviewed-artifact';(stage/name).write_bytes(payload)
                    (stage/'SHA256SUMS').write_text(hashlib.sha256(payload).hexdigest()+'  '+name+'\n')
                android=root/'builds/release-download/release-android/headscale-gateway-release.apk'
                if corrupt:android.write_bytes(b'fixture-altered')
                for name in ['VERSION','packaging/hacs/README.md','hacs.json','LICENSE','NOTICE','addons/headscale_gateway/config.yaml','yunohost/manifest.toml','custom_components/headscale_gateway/manifest.json','releases/current-sources/headscale-gateway-fuentes.zip']:
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('1.4.9' if name=='VERSION' else 'fixture')
                result=subprocess.run([sys.executable,'-c',assembly],cwd=root,capture_output=True,text=True)
                if corrupt:self.assertNotEqual(result.returncode,0)
                else:
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual((root/'releases/draft-assets/headscale-gateway-release.apk').read_bytes(),b'fixture-reviewed-artifact')
                    self.assertTrue((root/'releases/draft-assets/headscale-gateway-yunohost-1.4.9.zip').is_file())
                    self.assertIn('headscale-gateway-release.apk',(root/'releases/draft-assets/SHA256SUMS').read_text())

    def test_automatic_chain_does_not_depend_on_release_event_from_github_token(self):
        def workflow(name):return (ROOT/'.github/workflows'/name).read_text()
        detector=workflow('automatic-release.yml')
        self.assertIn('  schedule:',detector)
        self.assertIn("tags: ['v*']",detector)
        self.assertIn('  actions: write',detector)
        draft=workflow('release-draft.yml');prepare=workflow('prepare-public-release.yml');publish=workflow('publish-public-release.yml')
        self.assertIn('workflows: [Preparar entrega completa]',draft)
        self.assertIn('workflows: [Preparar y publicar release privada]',prepare)
        self.assertIn('Preparar distribución pública',publish)
        # Tres enlaces workflow_run: no exceder el límite de GitHub.
        self.assertEqual(len([draft,prepare,publish]),3)
        source=(ROOT/'.github/workflows/release-draft.yml').read_text()
        self.assertIn('gh release edit "$tag" --draft=false',source)
        self.assertIn("run['head_sha']==os.environ['GITHUB_SHA']",source)
        self.assertIn("'release-android'",source)

if __name__=='__main__':unittest.main()
