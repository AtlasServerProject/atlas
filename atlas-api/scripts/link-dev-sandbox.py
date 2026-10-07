#!/usr/bin/env python3
"""Link the existing sandbox account to VFSomente in the isolated dev database."""
import json, os, subprocess, uuid
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[1]
work=root/'.runtime/payment-sandbox'
state=json.loads((work/'state.json').read_text())
env=json.loads((work/'process-env.json').read_text())
assert env['ATLAS_MP_MODE']=='test'
assert state['db_port'] not in (5432,25432,55432)
assert env['ATLAS_DB_URL']==f"jdbc:postgresql://127.0.0.1:{state['db_port']}/postgres"
config=Path.home()/'.local/share/atlas-dev/fabric/config/atlas-database.properties'
dev=dict(line.split('=',1) for line in config.read_text().splitlines() if '=' in line and not line.startswith('#'))
assert dev['database']=='atlas_dev' and dev['port']=='25432' and dev['user']!='atlas_app'
pg=Path('/usr/lib/postgresql/18/bin')
def sql(port,user,password,database,query):
 process=subprocess.run([str(pg/'psql'),'-X','-h','127.0.0.1','-p',str(port),'-U',user,'-d',database,'-v','ON_ERROR_STOP=1','-At'],input=query,env={**os.environ,'PGPASSWORD':password},capture_output=True,text=True)
 if process.returncode:raise SystemExit('Database operation failed; no credentials printed.')
 return process.stdout.strip()
def core(query):return sql(dev['port'],dev['user'],dev['password'],dev['database'],query)
def api(query):return sql(state['db_port'],'atlas_api_bootstrap',env['ATLAS_BOOTSTRAP_PASSWORD'],'postgres',query)
order=str(uuid.UUID(state['order_id']))
player=json.loads(core("SELECT row_to_json(p) FROM (SELECT id,uuid,username FROM players WHERE lower(username)='vfsomente') p"))
assert player['username'].lower()=='vfsomente';player_id=int(player['id']);minecraft=str(uuid.UUID(player['uuid']))
account=str(uuid.UUID(api(f"SELECT user_id FROM atlas_web.orders WHERE id='{order}'")))
backup=work/('identity-before-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
backup.write_text(api(f"SELECT coalesce(json_agg(l),'[]'::json) FROM atlas_web.minecraft_links l WHERE user_id='{account}'"));backup.chmod(0o600)
subject=str(uuid.uuid4())
core(f"BEGIN; INSERT INTO site_identities(subject,player_id) VALUES('{subject}',{player_id}) ON CONFLICT(player_id) DO NOTHING; COMMIT;")
subject=str(uuid.UUID(core(f"SELECT subject FROM site_identities WHERE player_id={player_id}")))
existing=api(f"SELECT id FROM atlas_web.minecraft_links WHERE user_id='{account}' AND revoked_at IS NULL AND subject='{subject}' AND core_player_id={player_id} AND minecraft_uuid='{minecraft}' AND nickname='VFSomente'")
if not existing:
 link=str(uuid.uuid4())
 api(f"BEGIN; UPDATE atlas_web.minecraft_links SET revoked_at=now() WHERE user_id='{account}' AND revoked_at IS NULL; INSERT INTO atlas_web.minecraft_links(id,user_id,subject,core_player_id,minecraft_uuid,nickname,server,linked_at) VALUES('{link}','{account}','{subject}',{player_id},'{minecraft}','VFSomente','emerald',now()); INSERT INTO atlas_web.identity_audit(user_id,action,subject,request_id,created_at) VALUES('{account}','DEV_SANDBOX_LINK','{subject}','manual-test-only',now()); COMMIT;")
assert api(f"SELECT count(*) FROM atlas_web.minecraft_links WHERE user_id='{account}' AND revoked_at IS NULL AND subject='{subject}' AND core_player_id={player_id}")=='1'
assert api(f"SELECT snapshot->'identity'->>'nickname' FROM atlas_web.orders WHERE id='{order}'")!='VFSomente'
print('PASS: sandbox account linked to VFSomente in isolated dev database. Existing paid order preserved. Production unchanged.')
