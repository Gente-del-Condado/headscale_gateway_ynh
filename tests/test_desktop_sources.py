"""Los fuentes reutilizados pertenecen al runtime exacto, no a la versión Gateway."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import desktop_sources as sources
import publish_public_release as publisher
import check_release_reuse as public_check


class SharedDesktopSourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'
        self.cache.mkdir()
        (self.cache / 'source.tar.gz').write_bytes(b'exact upstream source')
        self.lock = {'electron_version': '45.0.0', 'sources': [
            {'name': 'source.tar.gz', 'url': 'https://example.invalid/source.tar.gz',
             'size': 21, 'sha256': sources.digest(self.cache / 'source.tar.gz')}],
            'runtimes': {'linux': {'sha256': 'a' * 64}}}
        self.output = self.root / 'dependencies'

    def test_identical_lock_reuses_set_but_runtime_or_source_change_selects_another(self):
        first = sources.prepare(self.cache, self.lock, self.output)
        self.assertEqual(first, sources.prepare(self.cache, self.lock, self.output))
        other = json.loads(json.dumps(self.lock))
        other['runtimes']['linux']['sha256'] = 'b' * 64
        self.assertNotEqual(sources.identity(other), sources.identity(self.lock))
        with self.assertRaisesRegex(ValueError, 'otro lock'):
            sources.prepare(self.cache, other, self.output)

    def test_corruption_and_extra_files_block_reuse(self):
        sources.prepare(self.cache, self.lock, self.output)
        (self.output / 'source.tar.gz').write_bytes(b'wrong source')
        with self.assertRaises(ValueError):
            sources.prepare(self.cache, self.lock, self.output)
        (self.output / 'source.tar.gz').write_bytes((self.cache / 'source.tar.gz').read_bytes())
        (self.output / 'unexpected').write_text('extra')
        with self.assertRaises(ValueError):
            sources.verify(self.output)

    def test_large_sources_preserve_order_combined_hash_and_stable_public_links(self):
        with patch.object(sources, 'MAX_SINGLE', 10), patch.object(sources, 'CHUNK', 8):
            result = sources.prepare(self.cache, self.lock, self.output)
            record = result['sources'][0]
            self.assertEqual(len(record['download_parts']), 3)
            self.assertNotIn('1.4.16', json.dumps(record))
            parts = json.loads((self.output / 'source.tar.gz.parts.json').read_text())
            combined = b''.join((self.output / p['name']).read_bytes() for p in parts['parts'])
            self.assertEqual(hashlib.sha256(combined).hexdigest(), self.lock['sources'][0]['sha256'])
            sources.verify(self.output)

    def test_published_dependencies_are_checked_and_never_reuploaded_or_made_latest(self):
        sources.prepare(self.cache, self.lock, self.output)
        files = sorted(self.output.iterdir())
        release = {'draft': False, 'prerelease': False, 'tag_name': sources.identity(self.lock),
                   'assets': [{'name': p.name, 'digest': 'sha256:' + sources.digest(p)} for p in files]}
        def response(url, timeout):
            import io
            stream = io.BytesIO((self.output / url.rsplit('/', 1)[1]).read_bytes())
            stream.status = 200
            return stream
        query = Mock(returncode=0, stdout=json.dumps(release))
        with patch.object(publisher.subprocess, 'run', return_value=query) as mutate, \
             patch.object(publisher, 'gh') as gh, \
             patch.object(publisher.urllib.request, 'urlopen', side_effect=response):
            result = sources.publish(self.output)
        self.assertTrue(result['reused'])
        self.assertEqual(mutate.call_count, 1)  # Solo consulta GET de la release.
        gh.assert_not_called()

    def test_invalid_paths_and_missing_hashes_are_rejected(self):
        for name in ['../source.tar.gz', '/source.tar.gz', 'bad\\source.tar.gz']:
            other = json.loads(json.dumps(self.lock))
            other['sources'][0]['name'] = name
            with self.assertRaises(ValueError):
                sources.identity(other)

    def test_seed_reads_old_release_without_mutating_it(self):
        import io
        record = self.lock['sources'][0]
        metadata = {'draft': False, 'prerelease': False, 'assets': [
            {'name': record['name'], 'size': record['size'], 'digest': 'sha256:' + record['sha256']}]}
        with patch.object(sources.subprocess, 'check_output', return_value=json.dumps(metadata)) as api, \
             patch.object(sources.urllib.request, 'urlopen', return_value=io.BytesIO((self.cache / record['name']).read_bytes())):
            sources.seed(self.lock, 'v1.4.16', self.output)
        api.assert_called_once_with(['gh', 'api', 'repos/' + sources.REPOSITORY + '/releases/tags/v1.4.16'], text=True)
        sources.verify(self.output)

    def test_first_publication_stays_out_of_latest_and_verifies_downloads(self):
        import io
        import shutil
        sources.prepare(self.cache, self.lock, self.output)
        tag = sources.identity(self.lock)
        calls = []
        def gh(*args):
            calls.append(args)
            if args[0] == 'api':
                if args[1].endswith('releases?per_page=100'):
                    return '[]'
                if args[1].endswith('/git/ref/heads/main'):
                    return json.dumps({'object': {'sha': 'a' * 40}})
                self.assertIn('make_latest=false', args)
                return json.dumps({'draft': True, 'prerelease': False, 'tag_name': tag, 'assets': []})
            if args[:2] == ('release', 'download'):
                name = args[args.index('--pattern') + 1]
                shutil.copy2(self.output / name, Path(args[args.index('--dir') + 1]) / name)
            return ''
        def download(url, timeout):
            stream = io.BytesIO((self.output / url.rsplit('/', 1)[1]).read_bytes())
            stream.status = 200
            return stream
        query = Mock(returncode=1, stderr='HTTP 404')
        with patch.object(publisher.subprocess, 'run', return_value=query), \
             patch.object(publisher, 'gh', side_effect=gh), \
             patch.object(publisher.urllib.request, 'urlopen', side_effect=download):
            result = sources.publish(self.output)
        self.assertEqual(len(result['files']), len(list(self.output.iterdir())))
        edit = next(args for args in calls if args[:2] == ('release', 'edit'))
        self.assertIn('--latest=false', edit)

    def test_remote_asset_mismatch_blocks_reuse(self):
        sources.prepare(self.cache, self.lock, self.output)
        files = sorted(self.output.iterdir())
        release = {'draft': False, 'prerelease': False, 'tag_name': sources.identity(self.lock),
                   'assets': [{'name': p.name, 'digest': 'sha256:' + '0' * 64} for p in files]}
        with patch.object(publisher.subprocess, 'run', return_value=Mock(returncode=0, stdout=json.dumps(release))), \
             patch.object(publisher, 'gh') as gh:
            with self.assertRaisesRegex(ValueError, 'No se reemplaza'):
                sources.publish(self.output)
        gh.assert_not_called()

    def test_next_gateway_version_only_publishes_installers_and_own_sources(self):
        # Ensayo de la siguiente entrega: sin compilar, tocar VERSION real ni subir.
        version = '1.4.17'
        payload = self.root / 'payload'
        payload.mkdir()
        dependencies = sources.prepare(self.cache, self.lock, payload / 'desktop-sources')
        for name in [
            'headscale-gateway-windows-amd64.zip', 'gateway-tray-linux-x64.tar.gz',
            f'headscale-gateway-homeassistant-{version}.zip', f'headscale-gateway-hacs-{version}.zip',
            f'headscale-gateway-yunohost-{version}.zip', f'headscale-gateway-go-sources-{version}.tar.gz',
            f'headscale-gateway-fuentes-publicos-{version}.zip', f'headscale-gateway-{version}-x86_64.flatpak',
        ]:
            (payload / name).write_bytes(b'fixture installer or own source')
        (payload / 'SHA256SUMS').write_text(''.join(sources.digest(p) + '  ' + p.name + '\n'
                                                   for p in sorted(payload.iterdir()) if p.is_file()))
        (payload / 'flatpak-source').mkdir()
        (payload / 'flatpak-source/README.md').write_text('fixture recipe')
        for name, body in {
            'VERSION': version, 'LICENSE': 'fixture license', 'NOTICE': 'fixture notices',
            'packaging/releases/README.md': 'fixture download guide',
            'packaging/desktop/electron-sources.lock.json': json.dumps(self.lock),
            'packaging/flatpak/files/es.gentedelcondado.HeadscaleGateway.png': 'fixture icon',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        captured = []
        def publish(repository, tag, files, notes):
            captured.append((repository, tag, {p.name for p in files}))
            self.assertIn(dependencies['release'], notes)
            return {'repository': repository, 'tag': tag}
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher, 'gh'), \
             patch.object(publisher, 'synchronize_public_tree'), \
             patch.object(publisher, 'public_repository', side_effect=lambda i: str(i)), \
             patch.object(publisher, 'publish_files', side_effect=publish), \
             patch.object(sys, 'argv', ['publish_public_release.py', str(payload), str(payload)]):
            publisher.main()
        self.assertEqual(len(captured), 4)
        for _, tag, names in captured:
            self.assertTrue(tag.startswith('v1.4.17'))
            self.assertNotIn('source.tar.gz', names)
            self.assertNotIn('DESKTOP-SOURCES.json', names)
            self.assertNotIn('RECONSTRUIR.md', names)
            self.assertIn('SHA256SUMS', names)
        self.assertEqual(dependencies['tag'], sources.identity(self.lock))

    def test_third_party_archive_or_fragment_in_gateway_payload_blocks_publication(self):
        payload = self.root / 'payload'
        payload.mkdir()
        for name in ['source.tar.gz', 'source.tar.gz.part-01', 'source.tar.gz.parts.json']:
            path = payload / name
            path.write_bytes(b'misplaced dependency')
            with self.assertRaisesRegex(ValueError, 'release reutilizable'):
                sources.gateway_files(payload, self.lock)
            path.unlink()

    def test_public_read_only_check_validates_existing_set_and_detects_altered_assets(self):
        sources.prepare(self.cache, self.lock, self.output)
        metadata = {'draft': False, 'prerelease': False, 'tag_name': sources.identity(self.lock),
                    'assets': [{'name': p.name, 'size': p.stat().st_size, 'digest': 'sha256:' + sources.digest(p)}
                               for p in self.output.iterdir()]}
        def read(url):
            if '/releases/tags/' in url:
                return json.dumps(metadata).encode()
            return (self.output / url.rsplit('/', 1)[1]).read_bytes()
        with patch.object(public_check, 'read', side_effect=read):
            self.assertEqual(public_check.check(self.lock), sources.references(self.lock)['release'])
            next(a for a in metadata['assets'] if a['name'] == 'source.tar.gz')['digest'] = 'sha256:' + '0' * 64
            with self.assertRaises(ValueError):
                public_check.check(self.lock)

    def test_only_missing_release_can_trigger_new_source_publication(self):
        import urllib.error
        with patch.object(public_check, 'read', side_effect=urllib.error.HTTPError('https://example.invalid', 404, 'missing', {}, None)):
            self.assertIsNone(public_check.check(self.lock, allow_missing=True))
        with patch.object(public_check, 'read', side_effect=urllib.error.HTTPError('https://example.invalid', 403, 'forbidden', {}, None)):
            with self.assertRaises(urllib.error.HTTPError):
                public_check.check(self.lock, allow_missing=True)


if __name__ == '__main__':
    unittest.main()
