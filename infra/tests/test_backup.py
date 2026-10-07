#!/usr/bin/env python3
"""Integration tests using a disposable PostgreSQL cluster and temporary Minecraft files."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts/backup-manager.py'
spec = importlib.util.spec_from_file_location('atlas_backup', MODULE)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='atlas-backup-test-')
        cls.root = Path(cls.temp.name)
        cls.bin = Path(subprocess.check_output(['pg_config', '--bindir'], text=True).strip())
        cls.socket = cls.root / 'socket'; cls.socket.mkdir()
        subprocess.run([str(cls.bin / 'initdb'), '-D', str(cls.root / 'pg'), '-A', 'trust', '-U', 'postgres', '--no-locale'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(cls.bin / 'pg_ctl'), '-D', str(cls.root / 'pg'), '-l', str(cls.root / 'postgres.log'), '-o',
                        f"-k {cls.socket} -c listen_addresses='' -p 55439", '-w', 'start'], check=True, stdout=subprocess.DEVNULL)
        cls.env = dict(os.environ, PGHOST=str(cls.socket), PGPORT='55439', PGUSER='postgres', PGDATABASE='source')
        for db in ('source', 'recovery'):
            subprocess.run(['createdb', '-w', db], env=cls.env, check=True)
        cls.sql("CREATE TABLE evidence (id integer PRIMARY KEY, value text); INSERT INTO evidence VALUES (1,'Atlas recuperação áéç');")

    @classmethod
    def tearDownClass(cls):
        subprocess.run([str(cls.bin / 'pg_ctl'), '-D', str(cls.root / 'pg'), '-m', 'immediate', '-w', 'stop'], check=True, stdout=subprocess.DEVNULL)
        cls.temp.cleanup()

    @classmethod
    def sql(cls, sql, database='source'):
        return subprocess.check_output(['psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-Atc', sql], env=dict(cls.env, PGDATABASE=database), text=True).strip()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.root))
        source = self.case / 'fabric'
        (source / 'world/region').mkdir(parents=True)
        (source / 'world/region/r.0.0.mca').write_bytes(b'ATLAS-WORLD\x00\xff')
        (source / 'server.properties').write_text('level-name=world\n')
        (source / 'logs').mkdir(); (source / 'logs/latest.log').write_text('not part of snapshot')
        self.manager = backup.Manager({'fabric_path': str(source), 'backup_path': str(self.case / 'backups'),
            'service': None, 'retention_days': 30, 'minimum_copies': 2,
            'postgres': {'host': str(self.socket), 'port': 55439, 'user': 'postgres', 'database': 'source'}})

    def test_roundtrip_and_validation(self):
        snapshot = self.manager.backup()
        target = self.case / 'recovered'
        self.manager.restore(snapshot, target, 'recovery')
        self.assertEqual((target / 'world/region/r.0.0.mca').read_bytes(), b'ATLAS-WORLD\x00\xff')
        self.assertFalse((target / 'logs').exists())
        self.assertIn('Atlas recuperação', self.sql('SELECT value FROM evidence', 'recovery'))
        with self.assertRaises(ValueError):
            self.manager.restore(snapshot, self.case / 'other', 'recovery')  # populated target database
        with self.assertRaises(ValueError):
            self.manager.restore(snapshot, self.case / 'other', 'source')  # production DB
        with self.assertRaises(ValueError):
            self.manager.restore(snapshot, self.manager.source / 'nested', 'recovery')
        with (snapshot / 'database.dump').open('ab') as stream:
            stream.write(b'corruption')
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            self.manager.verify(snapshot)

    def test_lock(self):
        with self.manager.locked():
            with self.assertRaises(RuntimeError):
                with self.manager.locked():
                    pass

    def test_dump_failure_restarts_and_cleans(self):
        with patch.object(self.manager, 'preflight'), patch.object(self.manager, 'active', side_effect=[True, False]), \
                patch.object(self.manager, 'control') as control, patch.object(backup, 'run', side_effect=RuntimeError('dump failed')):
            with self.assertRaises(RuntimeError):
                self.manager.backup()
            self.assertEqual([c.args[0] for c in control.call_args_list], ['stop', 'start'])
        self.assertFalse(list(self.manager.backups.glob('.partial-*')))
        self.assertFalse(list(self.manager.backups.glob('atlas-*')))

    def test_retention_preserves_minimum_and_unrelated_files(self):
        for index in range(4):
            snapshot = self.manager.backups / f'atlas-20000101T00000000000{index}Z'
            snapshot.mkdir()
            (snapshot / 'manifest.json').write_text(json.dumps({'format': 1, 'created_at': '2000-01-01T00:00:00+00:00'}))
        manual = self.manager.backups / 'manual-backup'; manual.mkdir()
        self.manager.prune()
        self.assertEqual(len(list(self.manager.backups.glob('atlas-*'))), 2)
        self.assertTrue(manual.exists())

    def test_failed_restore_is_transactional(self):
        env = self.manager.env
        data = self.case / 'failure.sql'
        data.write_text('DROP TABLE evidence; SELECT missing_function_for_test();')
        result = subprocess.run(['psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '--single-transaction', '-f', str(data)], env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.sql('SELECT count(*) FROM evidence'), '1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
