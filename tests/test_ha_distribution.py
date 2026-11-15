"""Contratos de exportación: fuentes confirmadas, aislamiento y validación previa."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ha_publisher', ROOT / 'tools/publish_ha_repository.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.source, self.target = self.tmp/'source', self.tmp/'target'
        for root in (self.source, self.target):
            root.mkdir()
            self.git(root, 'init', '--initial-branch=main')
        component = self.source/'custom_components/example'
        component.mkdir(parents=True)
        (component/'manifest.json').write_text('{"domain":"example"}')
        (self.source/'guide.md').write_text('Public guide')
        (self.source/'hacs.json').write_text('{}')
        (self.target/'custom_components/other').mkdir(parents=True)
        (self.target/'custom_components/other/keep').write_text('preserve')
        (self.target/'.github/workflows').mkdir(parents=True)
        (self.target/'.github/workflows/keep.yml').write_text('preserve')
        self.commit()

    def git(self, root, *args):
        return subprocess.run(['git', '-C', str(root), *args], check=True,
                              capture_output=True).stdout

    def commit(self):
        self.git(self.source, 'add', '.')
        self.git(self.source, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-m', 'fixture')

    def publish(self, readme='guide.md'):
        MODULE.prepare(self.source, self.target, 'example', readme)

    def test_uses_committed_files_and_preserves_other_components(self):
        (self.source/'guide.md').write_text('Uncommitted private draft')
        (self.source/'custom_components/example/private.key').write_text('not tracked')
        self.publish()
        self.assertEqual((self.target/'README.md').read_text(), 'Public guide')
        self.assertFalse((self.target/'custom_components/example/private.key').exists())
        self.assertEqual((self.target/'custom_components/other/keep').read_text(), 'preserve')
        self.assertEqual((self.target/'.github/workflows/keep.yml').read_text(), 'preserve')

    def test_missing_readme_does_not_modify_target(self):
        old = self.target/'custom_components/example'
        old.mkdir()
        (old/'keep').write_text('preserve')
        with self.assertRaises(ValueError):
            self.publish('missing.md')
        self.assertEqual((old/'keep').read_text(), 'preserve')

    def test_symlink_source_rejected_before_modification(self):
        (self.source/'custom_components/example/link').symlink_to('../../guide.md')
        self.commit()
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse((self.target/'custom_components/example').exists())

    def test_symlink_target_rejected(self):
        outside = self.tmp/'outside'
        outside.mkdir()
        (self.target/'custom_components/example').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(list(outside.iterdir()), [])

    def test_unsafe_readme_rejected(self):
        with self.assertRaises(ValueError):
            self.publish('../guide.md')


if __name__ == '__main__':
    unittest.main()
