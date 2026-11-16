"""El instalador no admite unidades ni rutas interpretables como órdenes."""
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('headscale_control_setup', str(ROOT / 'packaging/linux/native/headscale-gateway-setup-headscale'))
spec = importlib.util.spec_from_loader(loader.name, loader)
setup = importlib.util.module_from_spec(spec)
loader.exec_module(setup)


class ControlSetupTest(unittest.TestCase):
    def selection(self):
        return dict(instance='lab', allowed_uid=993, headscale_uid=992, headscale_gid=992,
                    binary='/usr/bin/headscale', config_path='/etc/headscale/config.yaml',
                    records_path='/var/lib/headscale/records.json', health_ca='',
                    state_dir='/var/lib/headscale-gateway-control/lab',
                    socket_path='/run/headscale-gateway-control/lab/control.sock',
                    unit='headscale.service', health_url='http://127.0.0.1:8080/health')

    def test_units_paths_and_identities_are_not_interpreted(self):
        setup.validate_selection(self.selection(), 'gateway.service')
        for key, value in [('instance','lab\nExecStart=/bin/sh'),('unit','headscale.service;id'),
                           ('config_path','/etc/headscale/../shadow'),('config_path','/etc/%n.yaml'),
                           ('allowed_uid',0),('allowed_uid',992),('health_url','https://example.test/health'),
                           ('health_url','http://user:secret@127.0.0.1/health'),
                           ('state_dir','/etc/headscale')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                data = self.selection(); data[key] = value
                setup.validate_selection(data, 'gateway.service')

    def test_root_helper_and_private_binding_have_separate_resources(self):
        unit = setup.render_unit(self.selection(), '/usr/local/libexec/headscale-gateway-control/lab/headscale-gateway')
        self.assertIn('User=root\n', unit)
        self.assertIn('NoNewPrivileges=true', unit)
        self.assertIn('ProtectSystem=strict', unit)
        self.assertIn('TimeoutStopSec=300s', unit)
        self.assertNotIn('/var/www/', unit)
        self.assertIn('headscale-control --spec /etc/headscale-gateway-control/lab.json', unit)

    def test_admin_write_rejects_symbolic_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'selected'
            outside = Path(directory) / 'other'; outside.write_text('conservar')
            target.symlink_to(outside)
            with self.assertRaises(ValueError):
                setup.atomic_write(target, b'alterado', 0o600)
            self.assertEqual(outside.read_text(), 'conservar')
