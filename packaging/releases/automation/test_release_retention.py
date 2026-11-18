"""La retención no destruye fuentes compartidos, entregas incompletas ni referencias Git."""
import hashlib
import io
from contextlib import redirect_stdout
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import release_retention as retention


def release(tag, identity=1, draft=False):
    return {'id': identity, 'tag_name': tag, 'draft': draft, 'prerelease': False,
            'body': '<!-- hgw-complete:' + 'a' * 40 + ' -->',
            'assets': [{'id': identity, 'name': 'installer.zip', 'size': 7, 'digest': 'sha256:' + 'b' * 64}]}


class RetentionTest(unittest.TestCase):
    def client(self, releases, forge='github'):
        client = Mock(forge=forge)
        client.releases.side_effect = lambda repo: releases if repo == retention.GENERAL or forge == 'forgejo' else []
        return client

    def plan(self, client):
        with patch.object(retention, 'keep_versions', return_value=[(1, 4, 17), (1, 4, 16)]):
            return retention.plan(client, Mock())

    def test_protects_two_completed_versions_pending_drafts_and_all_shared_sources(self):
        releases = [release('v1.4.19', 19), release('v1.4.18', 18, draft=True),
                    release('v1.4.17', 17), release('v1.4.16', 16), release('v1.4.15', 15),
                    release('desktop-sources-electron-45.0.0-abcd', 30),
                    release('desktop-sources-electron-44.0.0-efab', 31), release('unknown', 99)]
        report = self.plan(self.client(releases))
        self.assertEqual([r['tag'] for r in report['delete']], ['v1.4.15'])
        self.assertEqual(len(report['protected']), 7)

    def test_ynh_server_and_package_revisions_belong_to_the_same_version(self):
        repo = retention.OWNER + '/headscale_gateway_ynh'
        for tag in ['server-v1.4.16', 'v1.4.16-ynh1', 'v1.4.16-ynh2']:
            self.assertEqual(retention.version(tag, repo), (1, 4, 16))
        self.assertIsNone(retention.version('server-v1.4.16', retention.GENERAL))
        for tag in ['v1.04.16', 'v1.4.16-beta', 'source-v1.4.16', '../v1.4.16']:
            self.assertIsNone(retention.version(tag, repo))

    def test_numeric_versions_win_over_dates_and_lexicographic_order(self):
        client = Mock()
        client.releases.return_value = [release('v1.9.9'), release('v1.10.0'), release('v2.0.0'),
                                       release('v99.0.0', draft=True)]
        with patch.object(retention, 'verify_completed') as verify:
            self.assertEqual(retention.keep_versions(client), [(2, 0, 0), (1, 10, 0)])
        self.assertEqual(verify.call_count, 2)

    def test_missing_completion_receipts_or_two_completed_versions_blocks_deletion(self):
        client = Mock()
        client.releases.return_value = [release('v1.4.17')]
        with self.assertRaises(ValueError):
            retention.keep_versions(client)
        client.releases.return_value += [dict(release('v1.4.16'), body='unfinished')]
        with self.assertRaises(ValueError):
            retention.keep_versions(client)

    def test_missing_distribution_or_bad_sums_blocks_deletion(self):
        data = release('v1.4.17')
        sums = ('b' * 64 + '  installer.zip\n').encode()
        data['assets'].append({'id': 2, 'name': 'SHA256SUMS', 'size': len(sums),
                               'digest': 'sha256:' + hashlib.sha256(sums).hexdigest()})
        client = Mock()
        client.request.return_value = release('v1.4.17')
        with patch.object(retention, 'public_bytes', return_value=sums):
            retention.verify_completed(client, data)
            client.request.return_value['draft'] = True
            with self.assertRaises(ValueError):
                retention.verify_completed(client, data)
            client.request.return_value['draft'] = False
            data['assets'][0]['digest'] = 'sha256:' + 'f' * 64
            with self.assertRaises(ValueError):
                retention.verify_completed(client, data)

    def test_all_preconditions_checked_before_first_delete_and_never_deletes_tags(self):
        old = [release('v1.4.14', 14), release('v1.4.15', 15)]
        client = self.client(old)
        report = self.plan(client)
        client.request.side_effect = [old[0], dict(old[1], body='changed')]
        with self.assertRaises(ValueError):
            retention.execute(client, report)
        self.assertFalse(any(len(c.args) > 1 for c in client.request.call_args_list))
        client.request.reset_mock()
        client.request.side_effect = [old[0], old[1], old[0], None, old[1], None]
        with redirect_stdout(io.StringIO()):
            removed = retention.execute(client, report)
        self.assertEqual(len(removed), 2)
        deletes = [c.args for c in client.request.call_args_list if len(c.args) > 1]
        self.assertEqual(len(deletes), 2)
        self.assertTrue(all('/releases/' in args[0] and '/tags/' not in args[0] for args in deletes))

    def test_change_during_execution_stops_remaining_deletions(self):
        old = release('v1.4.15', 15)
        client = self.client([old])
        report = self.plan(client)
        client.request.side_effect = [old, dict(old, draft=True)]
        with self.assertRaises(ValueError):
            retention.execute(client, report)
        self.assertFalse(any(len(c.args) > 1 for c in client.request.call_args_list))

    def test_network_error_in_any_repository_prevents_planned_deletion(self):
        client = self.client([release('v1.4.15', 15)])
        client.releases.side_effect = [[release('v1.4.15', 15)], ValueError('offline')]
        with self.assertRaises(ValueError):
            self.plan(client)
        client.request.assert_not_called()

    def test_immutable_and_prereleases_are_protected(self):
        client = self.client([dict(release('v1.4.15'), immutable=True),
                              dict(release('v1.4.14'), prerelease=True)])
        self.assertEqual(self.plan(client)['delete'], [])

    def test_forgejo_cannot_clean_other_repositories_or_call_github_writes(self):
        client = self.client([release('v1.4.15', 15)], forge='forgejo')
        report = self.plan(client)
        self.assertEqual(report['delete'][0]['repository'], retention.FORGEJO_REPO)
        client.releases.assert_called_once_with(retention.FORGEJO_REPO)
        api = retention.API('forgejo', 'fixture-token')
        with patch.object(api.opener, 'open') as send:
            with self.assertRaises(ValueError):
                api.request('/repos/other/repository/releases/1', 'DELETE')
            for path in ['/repos/' + retention.FORGEJO_REPO,
                         '/repos/' + retention.FORGEJO_REPO + '/tags/v1.4.15',
                         '/repos/' + retention.FORGEJO_REPO + '/releases/0']:
                with self.assertRaises(ValueError):
                    api.request(path, 'DELETE')
            send.assert_not_called()

    def test_pagination_is_exhaustive_and_rejects_duplicate_page_or_truncation(self):
        api = retention.API()
        page = [release('v1.4.0', i) for i in range(1, 51)]
        with patch.object(api, 'request', side_effect=[page, [release('v1.4.1', 51)]]):
            self.assertEqual(len(api.releases(retention.GENERAL)), 51)
        with patch.object(api, 'request', side_effect=[page, [page[0]]]):
            with self.assertRaises(ValueError):
                api.releases(retention.GENERAL)
        with patch.object(api, 'request', return_value=page):
            with self.assertRaises(ValueError):
                api.releases(retention.GENERAL)

    def test_authenticated_requests_never_follow_redirects(self):
        self.assertIsNone(retention.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid'))
        with patch.dict('os.environ', {'HGW_FORGEJO_API': 'https://example.invalid'}):
            with self.assertRaises(ValueError):
                retention.API('forgejo', 'fixture-token')


if __name__ == '__main__':
    unittest.main()

