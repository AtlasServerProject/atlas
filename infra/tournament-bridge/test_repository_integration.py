"""Explicitly enabled tests against the isolated compatibility database only."""
import os
import unittest
import uuid
from pathlib import Path

@unittest.skipUnless(os.environ.get('ATLAS_TOURNAMENT_DB_TEST') == '1', 'isolated database opt-in required')
class DeadlineDatabaseTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from repository import Repository
        config = Path(__file__).resolve().parents[2] / 'atlas-api/.runtime/cobblemon-182-audit/config/atlas-database.properties'
        props = dict(line.split('=',1) for line in config.read_text().splitlines() if '=' in line and not line.startswith('#'))
        assert props['database']=='atlas_compat_182' and props['port']=='25432'
        self.connect=lambda:psycopg.connect(host=props['host'],port=props['port'],dbname=props['database'],user=props['user'],password=props['password'])
        self.repo=Repository(self.connect);self.id=uuid.uuid4()
        with self.connect() as db:
            db.execute("INSERT INTO atlas_tournaments(id,slug,title,capacity,state,created_by,registration_deadline) VALUES(%s,%s,'Torneio UU GEN 9',8,'OPEN','IsolatedTest',clock_timestamp()-interval '1 second')", (self.id,'test'+self.id.hex))
    def tearDown(self):
        with self.connect() as db:
            for table in ('atlas_tournament_announcements','atlas_tournament_entries'):
                db.execute('DELETE FROM '+table+' WHERE tournament_id=%s',(self.id,))
            db.execute('DELETE FROM atlas_tournaments WHERE id=%s',(self.id,))
    def test_expiry_once_and_blocks_stale_open_confirmation(self):
        event={'id':self.id,'state':'OPEN','revision':0}
        self.assertFalse(self.repo.current(event))
        self.repo.finish(event,'123','OPEN','Must not publish')
        self.repo.expire();self.repo.expire()
        with self.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM atlas_tournaments WHERE id=%s',(self.id,)).fetchone()[0],'CANCELLED')
            self.assertEqual(db.execute('SELECT count(*) FROM atlas_tournament_announcements WHERE tournament_id=%s',(self.id,)).fetchone()[0],1)
    def test_filled_event_survives_expiry_even_during_review(self):
        with self.connect() as db:
            for i in range(8):
                db.execute('INSERT INTO atlas_tournament_entries(tournament_id,player_uuid,player_name) VALUES(%s,%s,%s)',(self.id,uuid.uuid4(),'Test'+str(i)))
            db.execute("UPDATE atlas_tournaments SET state='FULL' WHERE id=%s",(self.id,))
        self.repo.expire();self.assertTrue(self.repo.current({'id':self.id,'state':'FULL','revision':0}))
        with self.connect() as db:
            db.execute("UPDATE atlas_tournaments SET state='REVIEW' WHERE id=%s",(self.id,))
        self.repo.expire()
        with self.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM atlas_tournaments WHERE id=%s',(self.id,)).fetchone()[0],'REVIEW')
