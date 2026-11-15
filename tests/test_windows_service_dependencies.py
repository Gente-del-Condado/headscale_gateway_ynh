"""Evita cargar un segundo propietario del SCM antes del motor en Windows."""
import os
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]

class WindowsDependenciesTest(unittest.TestCase):
    def test_acme_provider_does_not_import_caddy_service_initializer(self):
        dependencies=subprocess.check_output(['go','list','-mod=readonly','-deps','.'],cwd=ROOT/'src',
            env=dict(os.environ,GOOS='windows',GOARCH='amd64',CGO_ENABLED='0'),text=True).splitlines()
        self.assertFalse(any(name=='github.com/caddyserver/caddy/v2' or name.startswith('github.com/caddyserver/caddy/v2/') for name in dependencies))
        self.assertIn('github.com/gentedelcondado/headscale-gateway/internal/acmednstechnitium',dependencies)
        self.assertIn('github.com/caddyserver/certmagic',dependencies)
