"""Primer arranque, duplicados y accesos locales sin instalar servicios en el host."""
import importlib.machinery
import importlib.util
import json
import io
from contextlib import redirect_stdout, redirect_stderr
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packaging/common'))

def load(name,path):
    loader=importlib.machinery.SourceFileLoader(name,str(ROOT/path))
    spec=importlib.util.spec_from_loader(name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module

@unittest.skipUnless(os.name=='posix','Flatpak y acceso Linux')
class DesktopSessionTest(unittest.TestCase):
    def setUp(self):
        self.launcher=load('hgw_session_launcher', 'packaging/flatpak/files/headscale-gateway-launcher')

    def test_native_configurator_explains_login_and_never_resets_existing_account(self):
        configurator=load('hgw_native_configurator', 'packaging/linux/native/headscale-gateway-configure')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); output=io.StringIO()
            with patch.object(configurator,'getpass',return_value='fixture-password-123'), redirect_stdout(output):
                configurator.main(['--admin','fixture-admin'],data=root)
            self.assertIn('Usuario del panel: fixture-admin',output.getvalue())
            self.assertIn('http://127.0.0.1:9091/admin/',output.getvalue())
            self.assertIn('no la de sudo',output.getvalue())
            self.assertNotIn('fixture-password-123',output.getvalue())
            initial=root/'config/initial-admin.json'; before=initial.read_bytes()
            self.assertEqual(json.loads(before)['username'],'fixture-admin')
            with patch.object(configurator,'getpass',side_effect=AssertionError('must not ask again')), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit): configurator.main(['--admin','replacement'],data=root)
            self.assertEqual(initial.read_bytes(),before)

    def test_first_start_private_credentials_then_update_preserves_everything(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(self.launcher,'dialog',side_effect=['','fixture-admin','fixture-password-123','fixture-password-123']):
                database,startup,created=self.launcher.configure(root)
            self.assertTrue(created)
            credentials=root/'config/initial-admin.json'
            self.assertEqual(credentials.stat().st_mode&0o777,0o600)
            self.assertEqual(startup.stat().st_mode&0o777,0o600)
            self.assertEqual(json.loads(credentials.read_text())['username'],'fixture-admin')
            original=startup.read_bytes();secret=credentials.read_bytes()
            with patch.object(self.launcher,'dialog',side_effect=AssertionError('unexpected credential reset')):
                db2,_,created=self.launcher.configure(root)
            self.assertFalse(created);self.assertEqual(database,db2)
            self.assertEqual(startup.read_bytes(),original);self.assertEqual(credentials.read_bytes(),secret)

    def test_cancel_or_password_mismatch_creates_no_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(self.launcher,'dialog',side_effect=['','fixture-admin','fixture-password-123','different-password']):
                with self.assertRaises(ValueError):self.launcher.configure(root)
            self.assertFalse((root/'config/startup.json').exists())

    def test_legacy_identity_adopted_only_after_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);legacy=root/'gateway.sqlite';legacy.write_bytes(b'fixture database')
            key=root/'master.key';key.write_bytes(b'fixture secret')
            with patch.object(self.launcher,'dialog',return_value='') as question:
                database,startup,_=self.launcher.configure(root)
            self.assertEqual(database,legacy);self.assertEqual(question.call_count,1)
            self.assertEqual(legacy.read_bytes(),b'fixture database');self.assertEqual(key.read_bytes(),b'fixture secret')
            self.assertNotIn('initial_admin_file',json.loads(startup.read_text()))

    def test_url_never_targets_remote_or_embeds_a_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'startup.json'
            for value in ['example.test:9091','user:password@127.0.0.1:9091','127.0.0.1:9091?secret=value']:
                path.write_text(json.dumps({'listen_addr':value}))
                with self.assertRaises(ValueError):self.launcher.admin_url(path)
            path.write_text(json.dumps({'listen_addr':'127.0.0.1:23456'}))
            self.assertEqual(self.launcher.admin_url(path),'http://127.0.0.1:23456/admin/')

    def test_second_launch_opens_browser_without_another_engine(self):
        import fcntl
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)/'headscale-gateway';(data/'config').mkdir(parents=True)
            (data/'config/startup.json').write_text(json.dumps({'listen_addr':'127.0.0.1:23456'}))
            with (data/'session.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                with patch.dict(os.environ,{'XDG_DATA_HOME':directory}),patch.object(self.launcher,'wait_ready'),patch.object(self.launcher.subprocess,'run') as run,patch.object(self.launcher.subprocess,'Popen') as popen:
                    self.launcher.main()
                popen.assert_not_called();self.assertEqual(run.call_args.args[0],['xdg-open','http://127.0.0.1:23456/admin/'])

    def test_cli_help_does_not_open_desktop_or_configure(self):
        with patch.object(self.launcher.sys,'argv',['headscale-gateway-launcher','--help']),patch.object(self.launcher.os,'execv') as command,patch.object(self.launcher,'main') as main:
            self.launcher.entrypoint()
        command.assert_called_once_with('/app/bin/headscale-gateway',['headscale-gateway','--help']);main.assert_not_called()

    def test_autostart_is_background_only(self):
        with patch.object(self.launcher.sys,'argv',['headscale-gateway-launcher','--background']),patch.object(self.launcher.os,'execv') as command,patch.object(self.launcher,'main') as main:
            self.launcher.entrypoint()
        command.assert_not_called();main.assert_called_once_with(background=True)
