#!/usr/bin/env python3
"""Off-site copy tests against a disposable local restic repository (no network)."""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts/offsite-backup.py'
spec = importlib.util.spec_from_file_location('atlas_offsite', MODULE)
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)


@unittest.skipUnless(shutil.which('restic'), 'restic não instalado')
class OffsiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='atlas-offsite-test-')
        root = Path(self.temp.name)
        self.backups = root / 'snapshots'; self.backups.mkdir()
        (root / 'password').write_text('test-password-only\n')
        (root / 'env').write_text(f'RESTIC_REPOSITORY={root / "repo"}\n')
        self.config = {'backup_path': str(self.backups), 'env_file': str(root / 'env'),
                       'password_file': str(root / 'password'), 'cache_dir': str(root / 'cache'), 'keep_last': 1}
        self.manager = offsite.Offsite(self.config)
        self.manager.restic('init', '--quiet')
        self.root = root

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, name, world=b'ATLAS-WORLD\x00\xff'):
        path = self.backups / name; path.mkdir()
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w') as archive:
            info = tarfile.TarInfo('world/region/r.0.0.mca'); info.size = len(world)
            archive.addfile(info, io.BytesIO(world))
        (path / 'fabric.tar.gz').write_bytes(gzip.compress(payload.getvalue(), compresslevel=3))
        (path / 'database.dump').write_bytes(b'PGDMP fake dump ' + name.encode())
        files = {n: hashlib.sha256((path / n).read_bytes()).hexdigest() for n in ('database.dump', 'fabric.tar.gz')}
        (path / 'manifest.json').write_text(json.dumps({'format': 1, 'created_at': '2026-10-31T00:00:00+00:00',
                                                        'database': 'atlas', 'files': files}))
        return path

    def test_upload_is_idempotent_and_keeps_only_newest(self):
        self.snapshot('atlas-20261030T000000000000Z')
        self.manager.upload()
        self.manager.upload()  # Same snapshot: no new restic records.
        self.assertEqual(len(json.loads(self.manager.restic('snapshots', '--json', capture_output=True).stdout)), 2)
        self.snapshot('atlas-20261031T000000000000Z', b'NEWER-WORLD')
        self.manager.upload()
        complete, parts = self.manager.remote()
        self.assertEqual(complete, ['atlas-20261031T000000000000Z'])
        self.assertEqual(list(parts), complete)
        self.assertFalse(list(self.backups.glob('.offsite-*')))

    def test_fetch_rebuilds_verifiable_snapshot(self):
        source = self.snapshot('atlas-20261031T000000000000Z', b'WORLD-TO-RECOVER')
        self.manager.upload()
        target = self.manager.fetch(self.root / 'recovered')
        manifest = json.loads((target / 'manifest.json').read_text())
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(gzip.decompress((target / 'fabric.tar.gz').read_bytes()),
                         gzip.decompress((source / 'fabric.tar.gz').read_bytes()))
        self.assertEqual((target / 'database.dump').read_bytes(), (source / 'database.dump').read_bytes())
        with self.assertRaises(ValueError):
            self.manager.fetch(target)  # Populated destination.

    def test_corrupt_local_snapshot_is_not_recorded(self):
        path = self.snapshot('atlas-20261031T000000000000Z')
        manifest = json.loads((path / 'manifest.json').read_text())
        manifest['files']['fabric.tar.gz'] = '0' * 64
        (path / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            self.manager.upload()
        self.assertEqual(self.manager.remote(), ([], {}))

    def test_lock_shared_with_backup_manager(self):
        self.snapshot('atlas-20261031T000000000000Z')
        with self.manager.locked():
            with self.assertRaisesRegex(RuntimeError, 'andamento'):
                self.manager.upload()

    def test_credentials_validation(self):
        (self.root / 'env').write_text('RESTIC_REPOSITORY=s3:https://example.invalid/bucket\n')
        with self.assertRaisesRegex(ValueError, 'Chaves'):
            offsite.Offsite(self.config)


if __name__ == '__main__':
    unittest.main(verbosity=2)
