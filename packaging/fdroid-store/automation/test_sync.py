"""Contratos de origen, identidad, actualización y contenido del índice propio."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fdroid_store_sync', Path(__file__).with_name('sync.py'))
store = importlib.util.module_from_spec(spec); spec.loader.exec_module(store)


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.config = store.settings()
        self.app = self.config['apps'][0]
        self.report = {'package':self.app['id'], 'version':'1.4.19', 'version_code':10040190,
                       'certificate_sha256':self.app['certificate_sha256'], 'sha256':'a'*64,
                       'debuggable':False, 'unsigned':False}

    def release(self, tag='v1.4.19'):
        prefix=f"https://github.com/{self.app['source_repository']}/releases/download/{tag}/"
        return {'tag_name':tag,'draft':False,'prerelease':False,'assets':[
            {'name':name,'browser_download_url':prefix+name}
            for name in (self.app['apk_asset'],self.app['verification_asset'],'SHA256SUMS')]}

    def test_only_complete_stable_gateway_releases(self):
        for field in ('draft','prerelease'):
            value=self.release();value[field]=True
            self.assertIsNone(store.release_assets(value,self.app))
        self.assertIsNone(store.release_assets(self.release('desktop-sources-electron-45.0.0'),self.app))
        value=self.release();value['assets'].pop()
        self.assertIsNone(store.release_assets(value,self.app))
        self.assertIsNotNone(store.release_assets(self.release(),self.app))

    def test_redirecting_an_asset_to_other_repository_is_rejected(self):
        value=self.release();value['assets'][0]['browser_download_url']='https://github.com/other/repo/download/app.apk'
        with self.assertRaises(ValueError):store.release_assets(value,self.app)

    def test_identity_unsigned_debug_and_certificate_changes_are_rejected(self):
        store.validate_report(self.report,self.app,'v1.4.19')
        for field,value in [('package','org.example.app'),('certificate_sha256','b'*64),
                            ('version','1.4.18'),('version_code',0),('version_code',True),
                            ('debuggable',True),('unsigned',True),('sha256','invalid')]:
            report=dict(self.report,**{field:value})
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                store.validate_report(report,self.app,'v1.4.19')

    def test_two_versions_are_selected_and_do_not_rebuild_when_unchanged(self):
        releases=[self.release('v1.4.18'),self.release(),self.release('v1.4.17')]
        def fetch(url):
            if 'api.github.com' in url:return releases
            if '/v1.4.18/' in url:return dict(self.report,version='1.4.18',version_code=10040180)
            return self.report
        with patch.object(store,'read_json',side_effect=fetch):proposed=store.plan(self.config)
        self.assertEqual([p['version'] for p in proposed['packages']],['1.4.19','1.4.18'])
        previous=dict(proposed,generated_at=100)
        self.assertFalse(store.needs_update(proposed,previous,101))
        self.assertTrue(store.needs_update(proposed,previous,100+7*86400))
        changed=copy.deepcopy(proposed);changed['plan_sha256']='other'
        self.assertTrue(store.needs_update(changed,previous,101))
        self.assertTrue(store.needs_update(proposed,dict(previous,generated_at=200),101))

    def test_upstream_deletion_does_not_replace_store_with_older_apk(self):
        proposed={'plan_sha256':'new','packages':[{'app':'org.example.app','version_code':1}]}
        previous={'plan_sha256':'old','packages':[{'app':'org.example.app','version_code':2}]}
        with self.assertRaises(ValueError):store.needs_update(proposed,previous,100)

    def test_version_code_reuse_or_downgrade_is_rejected(self):
        def fetch(url):
            if 'api.github.com' in url:return [self.release(),self.release('v1.4.18')]
            if '/v1.4.18/' in url:return dict(self.report,version='1.4.18')
            return self.report
        with patch.object(store,'read_json',side_effect=fetch),self.assertRaises(ValueError):store.plan(self.config)

    def test_invalid_download_hash_is_rejected_before_inspecting_apk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'apk';path.write_bytes(b'altered')
            with patch.object(store.subprocess,'run') as command,self.assertRaises(ValueError):
                store.check_apk(path,{'sha256':'a'*64},self.app,Path(tmp))
            command.assert_not_called()

    def test_real_signature_must_match_even_when_checksum_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'apk';path.write_bytes(b'fixture')
            result=store.subprocess.CompletedProcess([],0,'Signer #1 certificate SHA-256 digest: '+'b'*64,'')
            with patch.object(store.subprocess,'run',return_value=result),self.assertRaises(ValueError):
                store.check_apk(path,{'sha256':store.digest(path)},self.app,Path(tmp))

    def test_configuration_rejects_unpinned_or_unsafe_sources(self):
        for mutate in (lambda c:c['apps'][0].update(certificate_sha256=''),
                       lambda c:c['apps'][0].update(source_repository='someone/foreign'),
                       lambda c:c['apps'][0].update(apk_asset='../app.apk'),
                       lambda c:c['apps'].append(copy.deepcopy(c['apps'][0]))):
            value=copy.deepcopy(self.config);mutate(value)
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'store.json').write_text(json.dumps(value))
                with self.assertRaises(ValueError):store.settings(root)

    def test_catalog_icon_is_copied_without_using_or_resigning_the_apk(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = Path(tmp) / 'metadata'
            store.copy_app_icon(store.ROOT, metadata, self.app['id'])
            relative = Path(self.app['id']) / 'en-US/images/icon.png'
            self.assertEqual((metadata / relative).read_bytes(),
                             (store.ROOT / 'metadata' / relative).read_bytes())
            with self.assertRaises(ValueError):
                store.copy_app_icon(Path(tmp), Path(tmp) / 'other', 'org.example.missing')

    def test_missing_corrupt_or_escaping_catalog_icons_block_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'; repo.mkdir()
            icon = repo / 'icon.png'; icon.write_bytes(b'fixture')
            data = {'metadata': {'icon': {'en-US': {'name': '/icon.png',
                    'sha256': store.digest(icon), 'size': icon.stat().st_size}}}}
            store.verify_icons(repo, {'org.example.app': data})
            for invalid in ({}, {'en-US': dict(data['metadata']['icon']['en-US'], sha256='a'*64)},
                            {'en-US': dict(data['metadata']['icon']['en-US'], name='/../icon.png')}):
                with self.subTest(icon=invalid), self.assertRaises(ValueError):
                    store.verify_icons(repo, {'org.example.app': {'metadata': {'icon': invalid}}})

    def test_workflow_uploads_only_site_and_never_uses_the_android_key(self):
        source=(store.ROOT/'.github/workflows/publish.yml').read_text()
        self.assertIn('FDROID_REPO_SIGNING_BUNDLE',source)
        self.assertNotIn('ANDROID_SIGNING_BUNDLE',source)
        self.assertIn('fdroid-store/site',source)
        job_env = source.split('    env:', 1)[1].split('    steps:', 1)[0]
        self.assertNotIn('runner.', job_env)
        self.assertIn("steps.plan.outputs.changed == 'true'",source)
        self.assertIn("cron: '43 * * * *'",source)


if __name__=='__main__':unittest.main()
