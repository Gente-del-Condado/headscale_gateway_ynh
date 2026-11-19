"""Contratos de lectura de releases y extracción del árbol sin historial."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('forgejo_source', Path(__file__).with_name('forgejo_source.py'))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class SourceContracts(unittest.TestCase):
    def archive(self, names, kind=tarfile.REGTYPE):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name in names:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                member.size = 1 if kind == tarfile.REGTYPE else 0
                archive.addfile(member, io.BytesIO(b'x') if member.size else None)
        stream.seek(0)
        return tarfile.open(fileobj=stream)

    def test_extract_only_single_root(self):
        with tempfile.TemporaryDirectory() as folder, self.archive(['root/src/main.go']) as archive:
            source.extract_archive(archive, folder)
            self.assertEqual((Path(folder) / 'src/main.go').read_bytes(), b'x')

    def test_reject_traversal_absolute_links_and_multiple_roots(self):
        cases = [(['root/../../outside'], tarfile.REGTYPE), (['/root/file'], tarfile.REGTYPE),
                 (['root/link'], tarfile.SYMTYPE), (['root/link'], tarfile.LNKTYPE),
                 (['root/file', 'other/file'], tarfile.REGTYPE), (['root/dir\\file'], tarfile.REGTYPE)]
        for names, kind in cases:
            with self.subTest(names=names, kind=kind), tempfile.TemporaryDirectory() as folder, self.archive(names, kind) as archive:
                with self.assertRaises(ValueError):
                    source.extract_archive(archive, folder)

    def test_reject_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as folder, self.archive(['root/file']) as archive:
            (Path(folder) / 'keep').write_text('existing')
            with self.assertRaises(ValueError):
                source.extract_archive(archive, folder)
            self.assertEqual((Path(folder) / 'keep').read_text(), 'existing')

    def test_only_explicitly_stable_releases(self):
        valid = {'tag_name': 'v1.4.9', 'draft': False, 'prerelease': False}
        source.validate_release(valid)
        for changes in [{'draft': True}, {'prerelease': True}, {'tag_name': 'v1.4.9-rc1'}, {'draft': None}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                source.validate_release(dict(valid, **changes))

    def test_completion_requires_receipt_and_all_destinations(self):
        sha = 'a' * 40
        general = {'draft': False, 'body': '<!-- hgw-complete:' + sha + ' -->'}
        release = {'draft': False, 'assets': [{'name': 'SHA256SUMS'}]}
        with patch.object(source, 'github', side_effect=[general, release, release, release]):
            self.assertTrue(source.completed('1.4.9', sha))
        with patch.object(source, 'github', side_effect=[general, release, None]):
            self.assertFalse(source.completed('1.4.9', sha))
        with patch.object(source, 'github', return_value={'draft': False, 'body': ''}):
            self.assertFalse(source.completed('1.4.9', sha))

    def test_candidate_cannot_select_an_unreviewed_or_changed_branch(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(source,'forgejo') as download:
                with self.assertRaises(ValueError):source.fetch('a'*40,'1.4.13',folder,'main')
                download.assert_not_called()
            with patch.object(source,'forgejo_json',return_value=[{'name':'codex/review','commit':{'id':'b'*40}}]),patch.object(source,'forgejo') as download:
                with self.assertRaises(ValueError):source.fetch('a'*40,'1.4.13',folder,'codex/review')
                download.assert_not_called()


class PublicationContracts(unittest.TestCase):
    def publisher(self):
        module_spec = importlib.util.spec_from_file_location('public_controller_publish', Path(__file__).with_name('publish_public.py'))
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def test_metadata_preserves_controller_and_unmanaged_files(self):
        module = self.publisher()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / 'metadata'
            metadata.mkdir()
            for name in ['README.md', 'LICENSE', 'NOTICE', 'icon.png']:
                (metadata / name).write_text('new')
            def clone(arguments, cwd):
                destination = Path(arguments[-1])
                (destination / '.github/workflows').mkdir(parents=True)
                (destination / '.github/workflows/release-public.yml').write_text('keep-workflow')
                (destination / 'automation').mkdir()
                (destination / 'automation/forgejo_source.py').write_text('keep-reader')
                (destination / 'unmanaged').write_text('keep-other')
            def inspect(destination, version):
                self.assertEqual((destination / '.github/workflows/release-public.yml').read_text(), 'keep-workflow')
                self.assertEqual((destination / 'automation/forgejo_source.py').read_text(), 'keep-reader')
                self.assertEqual((destination / 'unmanaged').read_text(), 'keep-other')
                self.assertEqual((destination / 'README.md').read_text(), 'new')
            with patch.object(module, 'run', side_effect=clone), patch.object(module, 'commit_and_push', side_effect=inspect):
                module.synchronize_controller(module.GENERAL, metadata, '1.4.9')

    def test_metadata_rejects_unexpected_files_and_destinations(self):
        module = self.publisher()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'unexpected').write_text('no')
            for repository in [module.GENERAL, 'another/repository']:
                with self.subTest(repository=repository), self.assertRaises(ValueError):
                    module.synchronize_controller(repository, root, '1.4.9')


class PortableManifestContracts(unittest.TestCase):
    def test_windows_paths_preserve_manifest_hashes(self):
        import json
        import types
        manifest = {'format': 1, 'version': '1.4.9', 'inputs': {'src/main.go': 'source-hash'}, 'outputs': {'yunohost/payload/engine': 'payload-hash'}}
        helpers = types.SimpleNamespace(input_hashes=lambda root: {'src\\main.go': 'source-hash'}, output_hashes=lambda root: {'yunohost\\payload\\engine': 'payload-hash'})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'VERSION').write_text('1.4.9')
            (root / 'git-install-manifest.json').write_text(json.dumps(manifest))
            with patch.dict('sys.modules', {'prepare_git_install': helpers}):
                source.verify_manifest(root)
                helpers.output_hashes = lambda root: {'yunohost\\payload\\engine': 'changed-payload'}
                with self.assertRaises(ValueError):
                    source.verify_manifest(root)



class MirrorMigrationContracts(unittest.TestCase):
    sha='a'*40

    def forgejo_metadata(self,path):
        if path.startswith('/releases/tags/'):
            return {'tag_name':'v1.4.19','draft':False,'prerelease':False}
        if path.startswith('/tags/'):
            return {'commit':{'sha':self.sha}}
        if path.startswith('/branches'):
            return [{'name':'codex/review','commit':{'id':self.sha}}]
        raise AssertionError(path)

    def test_requires_same_tag_in_both_origins(self):
        with patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'github-mirror'}), patch.object(source,'forgejo_json',side_effect=self.forgejo_metadata), patch.object(source,'mirror') as factory:
            factory.return_value.tag.return_value=self.sha
            source.verify_source_reference(self.sha,'1.4.19')
            factory.return_value.tag.assert_called_once_with('v1.4.19')
            factory.return_value.tag.return_value='b'*40
            with self.assertRaisesRegex(ValueError,'no coincide'):
                source.verify_source_reference(self.sha,'1.4.19')

    def test_candidate_requires_both_branches(self):
        with patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'github-mirror'}), patch.object(source,'forgejo_json',side_effect=self.forgejo_metadata), patch.object(source,'mirror') as factory:
            factory.return_value.branch.return_value='b'*40
            with self.assertRaisesRegex(ValueError,'no coincide'):
                source.verify_source_reference(self.sha,'1.4.19','codex/review')
            factory.return_value.branch.assert_called_once_with('codex/review')

    def test_missing_mirror_never_falls_back_to_forgejo_archive(self):
        with patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'github-mirror'}), patch.object(source,'forgejo_json',side_effect=self.forgejo_metadata), patch.object(source,'mirror',side_effect=ValueError('Falta el token')), patch.object(source,'forgejo') as download:
            with self.assertRaisesRegex(ValueError,'Falta el token'):
                source.fetch(self.sha,'1.4.19','unused')
            download.assert_not_called()

    def test_legacy_mode_is_explicit_and_invalid_mode_fails_closed(self):
        with patch.object(source,'forgejo_json',side_effect=self.forgejo_metadata), patch.object(source,'mirror') as factory:
            with patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'forgejo'}):
                source.verify_source_reference(self.sha,'1.4.19')
                factory.assert_not_called()
            with patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'wrong'}):
                with self.assertRaisesRegex(ValueError,'no autorizado'):
                    source.verify_source_reference(self.sha,'1.4.19')

    def test_mirror_download_checks_version_and_never_reads_forgejo_archive(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{'HGW_SOURCE_BACKEND':'github-mirror'}), patch.object(source,'forgejo_json',side_effect=self.forgejo_metadata), patch.object(source,'mirror') as factory, patch.object(source,'forgejo') as legacy:
            factory.return_value.tag.return_value=self.sha
            stream=io.BytesIO()
            with tarfile.open(fileobj=stream,mode='w:gz') as archive:
                entry=tarfile.TarInfo('source/VERSION');entry.size=5
                archive.addfile(entry,io.BytesIO(b'9.9.9'))
            stream.seek(0);factory.return_value.archive.return_value=stream
            with self.assertRaisesRegex(ValueError,'no coincide con VERSION'):
                source.fetch(self.sha,'1.4.19',folder)
            factory.return_value.archive.assert_called_once_with(self.sha)
            legacy.assert_not_called()

if __name__ == '__main__':
    unittest.main()
