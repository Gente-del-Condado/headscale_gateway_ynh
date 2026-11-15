"""La publicación no reemplaza recursos existentes ni oculta errores de acceso."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
SPEC = importlib.util.spec_from_file_location('public_assets', ROOT/'tools/publish_yunohost_assets.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicAssetsTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root/'VERSION').write_text('1.2.3')
        payload = root/'yunohost/payload'
        payload.mkdir(parents=True)
        for name in MODULE.NAMES:
            (payload/name).write_bytes(name.encode())
        self.release = {'tag_name':'server-v1.2.3', 'draft':False, 'prerelease':False,
                        'assets':[{'name':name,'digest':'sha256:'+MODULE.digest(payload/name)}
                                  for name in MODULE.NAMES]}
        self.enterContext(patch.object(MODULE, 'ROOT', root))
        self.enterContext(patch.object(MODULE, 'validate_package'))
        self.cli = self.enterContext(patch.object(MODULE, 'gh'))
        self.api = self.enterContext(patch.object(MODULE, 'api', return_value=self.release))
        self.downloads = self.enterContext(patch.object(MODULE, 'verify_downloads'))
        self.query = self.enterContext(patch.object(MODULE.subprocess, 'run'))
        self.query.return_value = subprocess.CompletedProcess([],0,json.dumps(self.release),'')

    def test_matching_published_assets_are_only_verified(self):
        MODULE.publish()
        self.cli.assert_not_called()
        self.downloads.assert_called_once()

    def test_mismatched_asset_is_never_overwritten(self):
        self.release['assets'][0]['digest'] = 'sha256:wrong'
        self.query.return_value.stdout = json.dumps(self.release)
        with self.assertRaises(ValueError): MODULE.publish()
        self.cli.assert_not_called()
        self.downloads.assert_not_called()

    def test_incomplete_published_release_is_rejected(self):
        self.release['assets'].pop()
        self.query.return_value.stdout = json.dumps(self.release)
        with self.assertRaises(ValueError): MODULE.publish()
        self.cli.assert_not_called()

    def test_access_error_does_not_create_a_release(self):
        self.query.return_value = subprocess.CompletedProcess([],1,'','HTTP 403')
        with self.assertRaises(RuntimeError): MODULE.publish()
        self.cli.assert_not_called()

    def test_multiple_drafts_require_review(self):
        self.query.return_value = subprocess.CompletedProcess([],1,'','HTTP 404')
        draft = dict(self.release, draft=True)
        self.api.return_value = [draft, draft]
        with self.assertRaises(ValueError): MODULE.publish()
        self.cli.assert_not_called()


if __name__ == '__main__': unittest.main()
