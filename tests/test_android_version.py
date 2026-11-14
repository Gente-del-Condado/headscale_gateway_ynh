"""La revisión móvil permite actualizar sin cambiar la versión del motor."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from android_version import release_version


class AndroidVersionTest(unittest.TestCase):
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
