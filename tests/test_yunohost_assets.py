"""Las etiquetas de recursos pertenecen al origen y sobreviven a su réplica."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_yunohost_assets as assets


class YunoHostAssetsTest(unittest.TestCase):
    def git(self, repository, *args):
        return subprocess.check_output(['git', '-C', str(repository), *args],
                                       stderr=subprocess.STDOUT, text=True).strip()

    def test_server_tag_survives_mirroring_and_does_not_move_with_documentation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin, replica, repository = (root/name for name in ('forgejo', 'github', 'package'))
            for bare in (origin, replica):
                subprocess.run(['git', 'init', '--bare', str(bare)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            repository.mkdir()
            self.git(repository, 'init', '-b', 'main')
            self.git(repository, 'config', 'user.name', 'Pruebas')
            self.git(repository, 'config', 'user.email', 'tests@example.invalid')
            (repository/'README.md').write_text('Fuentes originales\n')
            self.git(repository, 'add', 'README.md')
            self.git(repository, 'commit', '-m', 'Fuentes')
            source = self.git(repository, 'rev-parse', 'HEAD')
            self.git(repository, 'remote', 'add', 'origin', str(origin))
            self.git(repository, 'push', 'origin', 'HEAD:main', 'HEAD:upstream-source')
            (root/'VERSION').write_text('1.4.7\n')
            payload = root/'yunohost/payload'
            payload.mkdir(parents=True)
            for name in ('headscale-gateway-linux-amd64', 'headscale-gateway-linux-arm64', 'source.tar.gz'):
                (payload/name).write_bytes(b'recurso de prueba')
            workflow = root/'packaging/yunohost'/assets.WORKFLOW
            workflow.parent.mkdir(parents=True)
            workflow.write_text('name: Prueba\n')
            with patch.object(assets, 'ROOT', root):
                self.assertEqual(assets.prepare(repository)['source_commit'], source)
                (repository/'README.md').write_text('Documentación posterior\n')
                self.git(repository, 'add', 'README.md')
                self.git(repository, 'commit', '-m', 'Documentación')
                self.git(repository, 'push', 'origin', 'HEAD:upstream-source')
                self.assertEqual(assets.prepare(repository)['source_commit'], source)
            self.git(origin, 'push', '--mirror', str(replica))
            self.assertEqual(self.git(replica, 'rev-parse', 'refs/tags/server-v1.4.7'), source)

    def test_changed_tag_or_source_aborts_without_pushing(self):
        data = {'version': '1.4.7', 'source_commit': 'a'*40}
        with patch.object(assets, 'remote_target', return_value='b'*40), patch.object(assets.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'etiqueta'):
                assets.ensure_server_tag(Path('/example'), data)
            run.assert_not_called()
        with patch.object(assets, 'remote_target', return_value=None), patch.object(assets.subprocess, 'run') as run, \
                patch.object(assets.subprocess, 'check_output', return_value='b'*40+'\n'):
            with self.assertRaisesRegex(ValueError, 'fuentes públicos'):
                assets.ensure_server_tag(Path('/example'), data)
            self.assertEqual(run.call_count, 1)
            self.assertIn('fetch', run.call_args.args[0])
