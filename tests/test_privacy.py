"""La exportación no debe aceptar estado privado ni imprimir un secreto detectado."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('privacy_check', Path(__file__).resolve().parents[1]/'tools/check_privacy.py')
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTest(unittest.TestCase):
    def test_credentials_are_rejected_without_echoing_their_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'tools').mkdir()
            token = 'ghp_' + 'A'*36
            (root/'tools/fixture.txt').write_text('credential=' + token)
            with self.assertRaises(ValueError) as error:
                privacy.check(root)
            self.assertNotIn(token, str(error.exception))
            self.assertIn('tools/fixture.txt', str(error.exception))

    def test_database_is_rejected_even_without_detectable_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'gateway.sqlite').write_bytes(b'\x00'*8)
            with self.assertRaisesRegex(ValueError, 'archivo de estado'):
                privacy.check(root)

    def test_ignored_credentials_inside_sources_are_still_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'src').mkdir()
            (root/'src/credentials.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'src/credentials.json'):
                privacy.check(root)

    def test_hashes_and_normal_sources_are_not_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'manifest.json').write_text('{"file": "' + 'a'*64 + '"}')
            privacy.check(root)
