"""Una creación reciente no debe depender de la caché de listas de GitHub."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import publish_yunohost_assets as assets


class YunohostAssetsTest(unittest.TestCase):
    def test_creation_uses_response_when_listing_is_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'VERSION').write_text('1.4.8\n')
            payload = root / 'yunohost/payload'
            payload.mkdir(parents=True)
            for name in assets.NAMES:
                (payload / name).write_bytes(name.encode())
            draft = {'id': 123, 'tag_name': 'server-v1.4.8', 'draft': True, 'assets': []}
            published = dict(draft, draft=False, prerelease=False)

            def api(path):
                if path == 'releases?per_page=100':
                    return []  # La lista sigue vacía aunque el POST haya terminado.
                if path == 'git/ref/heads/main':
                    return {'object': {'sha': 'a' * 40}}
                if path == 'releases/tags/server-v1.4.8':
                    return published
                raise AssertionError(path)

            def gh(*arguments):
                if arguments[0] == 'api':
                    return json.dumps(draft)
                return ''

            missing = subprocess.CompletedProcess([], 1, '', 'HTTP 404: Not Found')
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'validate_package'), \
                    patch.object(assets.subprocess, 'run', return_value=missing), \
                    patch.object(assets, 'api', side_effect=api) as query, \
                    patch.object(assets, 'gh', side_effect=gh) as command, \
                    patch.object(assets, 'verify_downloads') as verify:
                assets.publish()
            self.assertEqual(sum(c.args == ('releases?per_page=100',) for c in query.call_args_list), 1)
            self.assertEqual(sum(c.args[:2] == ('release', 'upload') for c in command.call_args_list), 3)
            verify.assert_called_once()

    def test_published_resource_with_other_digest_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'VERSION').write_text('1.4.8\n')
            payload = root / 'yunohost/payload'
            payload.mkdir(parents=True)
            for name in assets.NAMES:
                (payload / name).write_bytes(b'expected')
            release = {'draft': False, 'assets': [{'name': assets.NAMES[0], 'digest': 'sha256:other'}]}
            response = subprocess.CompletedProcess([], 0, json.dumps(release), '')
            with patch.object(assets, 'ROOT', root), patch.object(assets, 'validate_package'), \
                    patch.object(assets.subprocess, 'run', return_value=response), \
                    patch.object(assets, 'gh') as command:
                with self.assertRaisesRegex(ValueError, 'No se reemplaza'):
                    assets.publish()
            command.assert_not_called()
