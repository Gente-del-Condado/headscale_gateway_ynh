"""La tienda solo anuncia imágenes públicas completas de fuentes identificados."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import images


class ImageStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.old = Path.cwd()
        self.root = Path(self.temporary.name)
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.old)
        self.git('init', '-q')
        self.git('config', 'user.name', 'fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        for app in images.APPS:
            folder = self.root / app
            folder.mkdir()
            (folder / 'config.yaml').write_text(f'slug: {app}\nversion: "1.0.0"\narch: [amd64, aarch64]\n')
            (folder / 'Dockerfile').write_text('FROM scratch\n')
        (self.root / 'repository.yaml').write_text('name: fixture\n')
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.git('update-ref', 'refs/remotes/origin/main', self.sha)
        self.git('update-ref', 'refs/remotes/origin/build-source', self.sha)

    def git(self, *args):
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL)

    def commit(self):
        self.git('add', '--all')
        self.git('commit', '-qm', 'fixture')

    def select(self):
        with patch.object(images, 'refresh'), patch.dict(os.environ, {'GITHUB_REPOSITORY': images.REPOSITORY}):
            return images.select()

    def test_initial_plan_has_eight_native_jobs_with_pinned_tree_and_version(self):
        matrix, apps, sha = self.select()
        self.assertEqual(len(matrix['include']), 8)
        self.assertEqual(len(apps), 4)
        self.assertEqual(sha, self.sha)
        self.assertEqual({j['runner'] for j in matrix['include']}, {'ubuntu-24.04', 'ubuntu-24.04-arm'})
        self.assertTrue(all(j['version'] == '1.0.0' and len(j['tree']) == 40 for j in matrix['include']))

    def test_published_trees_are_not_rebuilt_or_retagged(self):
        _, apps, _ = self.select()
        records = self.root / '.images'
        records.mkdir()
        for item in apps:
            (records / (item['app'] + '.json')).write_text(json.dumps(item))
        self.commit()
        self.git('update-ref', 'refs/remotes/origin/main', self.git('rev-parse', 'HEAD').strip())
        self.assertEqual(self.select()[1], [])

    def test_modifying_an_existing_version_or_downgrading_is_rejected(self):
        _, apps, _ = self.select()
        records = self.root / '.images'
        records.mkdir()
        value = dict(apps[0], tree='a' * 40)
        (records / (value['app'] + '.json')).write_text(json.dumps(value))
        self.commit()
        self.git('update-ref', 'refs/remotes/origin/main', self.git('rev-parse', 'HEAD').strip())
        with self.assertRaisesRegex(ValueError, 'Incrementa'):
            self.select()
        value['version'] = '2.0.0'
        (records / (value['app'] + '.json')).write_text(json.dumps(value))
        self.commit()
        self.git('update-ref', 'refs/remotes/origin/main', self.git('rev-parse', 'HEAD').strip())
        with self.assertRaisesRegex(ValueError, 'retrocede'):
            self.select()

    def test_unknown_application_or_unsupported_architecture_blocks_publication(self):
        folder = self.root / 'unreviewed'
        folder.mkdir()
        (folder / 'config.yaml').write_text('slug: unreviewed\n')
        self.commit()
        self.git('update-ref', 'refs/remotes/origin/build-source', self.git('rev-parse', 'HEAD').strip())
        with self.assertRaisesRegex(ValueError, 'sin pruebas'):
            self.select()

    def test_multiarchitecture_index_requires_both_platforms_exactly_once(self):
        entries = [{'platform': {'os':'linux', 'architecture':a}} for a in ['amd64','arm64']]
        images.validate_index({'manifests': entries})
        for invalid in [[], entries[:1], entries + entries[:1]]:
            with self.assertRaises(ValueError):
                images.validate_index({'manifests': invalid})

    def test_missing_public_access_cannot_change_the_store(self):
        _, apps, _ = self.select()
        with patch.dict(os.environ, {'GITHUB_REPOSITORY': images.REPOSITORY}), \
             patch.object(images, 'inspect', return_value=None), \
             patch.object(images, 'run') as run, \
             patch.object(images, 'registry', side_effect=ValueError('invalid index')), \
             self.assertRaises(ValueError):
            images.publish(apps[:1])
        self.assertFalse(any(call.args and call.args[0]=='git' for call in run.call_args_list))
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.sha)

    def test_foreign_repository_and_image_names_are_rejected(self):
        with patch.dict(os.environ, {'GITHUB_REPOSITORY':'other/repository'}):
            with self.assertRaises(ValueError):
                self.select_foreign()
        with self.assertRaises(ValueError):
            images.image_name('../other')
        with self.assertRaises(ValueError):
            images.registry('https://example.invalid/image:1.0.0')

    def select_foreign(self):
        with patch.object(images, 'refresh'):
            return images.select()


if __name__ == '__main__':
    unittest.main()
