"""Empaquetado nativo y separación de fuentes sin alterar los ejecutables."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import package_linux
import prepare_public_release
import prepare_flatpak
import desktop_compliance
from test_desktop_compliance import DesktopComplianceTest

class PublicDistributionTest(unittest.TestCase):
    def test_native_package_layout_keeps_helper_adjacent_and_data_outside_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);binary=root/'binary';helper=root/'helper'
            binary.write_bytes(b'ELF motor');helper.write_bytes(b'ELF helper')
            stage=root/'stage';package_linux.stage(stage,binary,helper)
            self.assertTrue((stage/'usr/bin/headscale-gateway').is_symlink())
            target=(stage/'usr/bin/headscale-gateway').resolve()
            self.assertEqual(target.read_bytes(),binary.read_bytes())
            self.assertEqual((target.parent/'hgw-ca-helper').read_bytes(),helper.read_bytes())
            self.assertFalse((stage/'var').exists())
            unit=(stage/'usr/lib/systemd/system/headscale-gateway.service').read_text()
            self.assertIn('User=headscale-gateway',unit)
            self.assertIn('ExecCondition=',unit)
            self.assertNotIn('/usr/local',unit)
            self.assertNotIn('rm -rf',package_linux.POST+package_linux.REMOVE)

    def test_light_desktop_preserves_runtime_and_publishes_exact_sources(self):
        fixture=DesktopComplianceTest();fixture.setUp()
        try:
            fixture.prepare()
            before=desktop_compliance.verify(fixture.runtime,'linux',fixture.lock)
            output=fixture.root/'public';output.mkdir()
            with patch.object(prepare_public_release,'verify_complete',side_effect=lambda r,p:desktop_compliance.verify(r,p,fixture.lock)):
                result=prepare_public_release.detach_sources(fixture.runtime,'linux',output,'https://example.invalid/releases/v1/')
            self.assertEqual(result['runtime_files'],before['runtime_files'])
            self.assertFalse((fixture.runtime/'legal/sources').exists())
            self.assertEqual(prepare_public_release.digest(output/'source.tar.xz'),fixture.lock['sources'][0]['sha256'])
            self.assertEqual(result['external_sources'][0]['download'],'https://example.invalid/releases/v1/source.tar.xz')
            self.assertTrue((fixture.runtime/'legal/LICENSES.chromium.html').exists())
        finally:fixture.doCleanups();fixture.temp.cleanup()

    def test_archives_cannot_escape_or_link_outside_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside','unsafe')
            with zipfile.ZipFile(archive) as z:
                with self.assertRaises(ValueError):prepare_public_release.safe_extract(z,root/'stage')
            self.assertFalse((root/'outside').exists())

    def test_flatpak_contains_full_engine_and_network_only_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            result=prepare_flatpak.prepare(Path(temporary)/'flatpak')
            manifest=json.loads((result/'es.gentedelcondado.HeadscaleGateway.json').read_text())
            self.assertEqual(manifest['finish-args'],['--share=network'])
            self.assertEqual(manifest['command'],'headscale-gateway-launcher')
            sources=manifest['modules'][0]['sources']
            self.assertTrue(any('headscale-gateway-linux-amd64' in s.get('url','') for s in sources))
            self.assertNotIn('Gateway-Tray',json.dumps(manifest))
            self.assertFalse((result/'es.gentedelcondado.HeadscaleGateway.json.in').exists())
            self.assertFalse((result/'files/es.gentedelcondado.HeadscaleGateway.metainfo.xml.in').exists())
            self.assertTrue((result/'files/notices/third_party/go').is_dir())
