"""La revisión móvil permite actualizar sin cambiar la versión del motor."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from android_version import release_version
from set_version import mobile_documents


class AndroidVersionTest(unittest.TestCase):
    def test_current_guides_follow_android_version_and_preserve_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = Path(__file__).resolve().parents[1]
            for name in ('android/README.md', 'packaging/android/play/PUBLICACION.md'):
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text((source / name).read_text())
            (root / 'VERSION').write_text('2.0.1\n')
            (root / 'android/release.properties').write_text('revision=5\n')
            with self.assertRaisesRegex(ValueError, 'obsoleta'):
                mobile_documents(root, check=True)
            mobile_documents(root)
            mobile_documents(root, check=True)
            guide = (root / 'android/README.md').read_text()
            self.assertIn('**2.0.1-android.5**', guide)
            self.assertIn('`20000015`', guide)
            self.assertIn('## Desconectar las aplicaciones en 1.4.12', guide)
            self.assertIn('versionCode: `20000015`', (root / 'packaging/android/play/PUBLICACION.md').read_text())

    def test_revision_update_and_next_engine_version_remain_monotonic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'android').mkdir()
            (root / 'VERSION').write_text('1.4.7\n')
            prop = root / 'android/release.properties'
            prop.write_text('revision=4\n')
            previous = release_version(root)
            prop.write_text('revision=5\n')
            current = release_version(root)
            self.assertEqual(previous, ('1.4.7', 10040074))
            self.assertEqual(current, ('1.4.7-android.5', 10040075))
            self.assertGreater(current[1], previous[1])
            prop.write_text('revision=9\n')
            last = release_version(root)
            (root / 'VERSION').write_text('1.4.8\n')
            prop.write_text('revision=0\n')
            self.assertGreater(release_version(root)[1], last[1])
            prop.write_text('revision=10\n')
            with self.assertRaisesRegex(ValueError, 'Revisión'):
                release_version(root)
