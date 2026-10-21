import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('prune_backups', Path(__file__).parents[1] / 'scripts/prune-old-backups.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Manager:
    def __init__(self, root, invalid=()):
        self.backups = root
        self.invalid = invalid

    def verify(self, path):
        if path.name in self.invalid:
            raise ValueError('Corrupt checksum')


def seed(root, number):
    path = root / f'atlas-202610{number:02d}T000000000000Z'
    path.mkdir()
    (path / 'payload').write_text('fixture')
    return path


class CleanupTests(unittest.TestCase):
    def test_preserves_two_newest_and_unrelated_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = [seed(root, n) for n in range(1, 5)]
            unrelated = root / 'other-data'
            unrelated.mkdir()
            module.prune(Manager(root), apply=True)
            self.assertEqual([p.exists() for p in entries], [False, False, True, True])
            self.assertTrue(unrelated.exists())

    def test_corrupt_newest_stays_for_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = [seed(root, n) for n in range(1, 5)]
            module.prune(Manager(root, [entries[-1].name]), apply=True)
            self.assertEqual([p.exists() for p in entries], [False, True, True, True])

    def test_no_deletion_without_two_verified_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = seed(root, 1), seed(root, 2)
            with self.assertRaises(RuntimeError):
                module.prune(Manager(root, [second.name]), apply=True)
            self.assertTrue(first.exists() and second.exists())

    def test_dry_run_does_not_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = [seed(root, n) for n in range(1, 4)]
            self.assertEqual(len(module.prune(Manager(root))), 1)
            self.assertTrue(all(p.exists() for p in entries))


if __name__ == '__main__':
    unittest.main()
