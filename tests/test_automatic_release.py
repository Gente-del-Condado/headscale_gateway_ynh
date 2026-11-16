"""Un único publicador público debe bloquear entregas si falla su validación."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import android_ci_signing as signing


class AutomaticReleaseTest(unittest.TestCase):
    def test_public_control_is_the_only_automatic_publisher(self):
        self.assertEqual({p.name for p in (ROOT/'.github/workflows').iterdir()}, {'quality.yml', 'platforms.yml'})
        self.assertFalse((ROOT/'.forgejo/workflows').exists())
        control = (ROOT/'packaging/releases/.github/workflows/release-public.yml').read_text()
        self.assertIn("cron: '17 * * * *'", control)
        self.assertIn('needs: [plan, linux, windows, homeassistant]', control)
        self.assertIn('govulncheck@v1.9.0 -scan module', control)
        self.assertIn('npm audit --include=dev --audit-level=low', control)
        self.assertIn('tools/verify.sh', control)
        self.assertIn('python3 automation/publish_public.py', control)
        quality = (ROOT/'.github/workflows/quality.yml').read_text()
        self.assertIn('pull_request:', quality)
        self.assertIn('name: Seguridad de dependencias', quality)

    def test_signing_rejects_missing_or_different_identity_without_logging_bundle(self):
        for value in ['', '{"format":1,"password":"fixture-private-value"}']:
            with patch.dict(os.environ, {'HGW_ANDROID_SIGNING_BUNDLE':value}):
                with self.assertRaises(ValueError) as error:
                    with signing.signing_profile():
                        self.fail('No debe aceptar otra identidad')
                self.assertNotIn('fixture-private-value', str(error.exception))


if __name__ == '__main__':
    unittest.main()
