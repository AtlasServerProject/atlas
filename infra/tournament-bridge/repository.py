"""Database boundary; reuse the server's existing private connection resolver."""
import importlib.util
from pathlib import Path
from psycopg.rows import dict_row
_spec = importlib.util.spec_from_file_location('atlas_existing_relay', Path(__file__).resolve().parents[1] / 'moderation-relay/relay.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
connection = _module.connection

class Repository:
    def __init__(self, connect=connection):
        self.connect = connect

    def expire(self):
        with self.connect() as db:
            db.execute('SELECT pg_advisory_xact_lock(13842016)')
            rows = db.execute("UPDATE atlas_tournaments SET state='CANCELLED',last_error=NULL,updated_at=clock_timestamp() WHERE state IN ('CREATING','OPEN','REVIEW') AND registration_deadline<=clock_timestamp() AND (SELECT count(*) FROM atlas_tournament_entries e WHERE e.tournament_id=atlas_tournaments.id AND e.active)<capacity RETURNING id,title,capacity").fetchall()
            for id,title,capacity in rows:
                db.execute('UPDATE atlas_tournament_announcements SET delivered=true WHERE tournament_id=%s AND NOT delivered', (id,))
                db.execute('INSERT INTO atlas_tournament_announcements(tournament_id,message) VALUES(%s,%s)', (id,f'{title} cancelado: o prazo de inscrição terminou sem preencher as {capacity} vagas.'))

    def next(self):
        with self.connect() as db:
            db.row_factory = dict_row
            return db.execute("SELECT * FROM atlas_tournaments WHERE state IN ('CREATING','OPEN','FULL') AND retry_at<=now() AND (state IN ('CREATING','FULL') OR revision>synced_revision) ORDER BY created_at LIMIT 1").fetchone()

    def entries(self, id, active=True):
        with self.connect() as db:
            db.row_factory = dict_row
            return db.execute('SELECT * FROM atlas_tournament_entries WHERE tournament_id=%s' + (' AND active' if active else ''), (id,)).fetchall()

    def current(self, event):
        with self.connect() as db:
            row = db.execute("SELECT state,revision FROM atlas_tournaments WHERE id=%s AND (state='FULL' OR registration_deadline>clock_timestamp())", (event['id'],)).fetchone()
            return row == (event['state'], event['revision'])

    def finish(self, event, remote_id, state, message=None):
        with self.connect() as db:
            result = db.execute("UPDATE atlas_tournaments SET remote_id=%s,state=%s,synced_revision=%s,last_error=NULL,updated_at=now() WHERE id=%s AND state=%s AND revision=%s AND (state='FULL' OR registration_deadline>clock_timestamp()) RETURNING id", (remote_id,state,event['revision'],event['id'],event['state'],event['revision'])).fetchone()
            if result and message:
                db.execute('INSERT INTO atlas_tournament_announcements(tournament_id,message) VALUES(%s,%s)', (event['id'],message))

    def fail(self, event, reason, review=False, delay=300):
        with self.connect() as db:
            db.execute("UPDATE atlas_tournaments SET last_error=%s,state=CASE WHEN %s THEN 'REVIEW' ELSE state END,retry_at=now()+(%s * interval '1 second') WHERE id=%s AND state=%s AND revision=%s", (reason,review,delay,event['id'],event['state'],event['revision']))
