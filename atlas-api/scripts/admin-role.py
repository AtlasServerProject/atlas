#!/usr/bin/env python3
"""Grant/revoke ADMIN for an existing verified account. Uses the migration role; never creates users/passwords."""
import argparse
import os
from pathlib import Path
import subprocess
import uuid
from urllib.parse import urlsplit

parser=argparse.ArgumentParser()
parser.add_argument('--user-id',type=uuid.UUID,required=True)
parser.add_argument('--role',choices=['USER','ADMIN'],required=True)
parser.add_argument('--actor',required=True)
parser.add_argument('--reason',required=True)
args=parser.parse_args()
if not args.reason.strip() or len(args.reason)>500 or not args.actor.strip() or len(args.actor)>100:
    raise SystemExit('A nonempty reason (<=500 chars) and actor (<=100 chars) are required.')
env=os.environ.copy()
local=Path(__file__).resolve().parents[1]/'.env'
if local.exists():
    for line in local.read_text().splitlines():
        if line and not line.startswith('#') and '=' in line:
            key,value=line.split('=',1);env.setdefault(key,value)
for key in ['ATLAS_DB_URL','ATLAS_MIGRATION_USERNAME','ATLAS_MIGRATION_PASSWORD']:
    if not env.get(key):raise SystemExit(f'Configure {key} outside source control.')
url=urlsplit(env['ATLAS_DB_URL'].removeprefix('jdbc:'))
if url.scheme!='postgresql' or not url.hostname or url.username or url.query:
    raise SystemExit('Expected a plain PostgreSQL JDBC URL; configure credentials separately.')
env.update({'PGPASSWORD':env['ATLAS_MIGRATION_PASSWORD'],'ATLAS_ROLE_TARGET':str(args.user_id),'ATLAS_ROLE_VALUE':args.role,'ATLAS_ROLE_ACTOR':args.actor,'ATLAS_ROLE_REASON':args.reason})
sql=r'''
\set ON_ERROR_STOP on
\getenv target ATLAS_ROLE_TARGET
\getenv desired ATLAS_ROLE_VALUE
\getenv actor ATLAS_ROLE_ACTOR
\getenv reason ATLAS_ROLE_REASON
BEGIN;
SELECT pg_advisory_xact_lock(21749001);
SELECT id FROM atlas_web.users WHERE id=:'target'::uuid AND email_verified FOR UPDATE;
WITH previous AS MATERIALIZED (SELECT id,role FROM atlas_web.users WHERE id=:'target'::uuid AND email_verified),
changed AS (UPDATE atlas_web.users u SET role=:'desired' FROM previous p WHERE u.id=p.id
AND (:'desired'='ADMIN' OR p.role<>'ADMIN' OR (SELECT count(*) FROM atlas_web.users WHERE role='ADMIN')>1)
RETURNING u.id,p.role)
INSERT INTO atlas_web.auth_audit(id,actor,target_user_id,action,previous_role,new_role,reason)
SELECT gen_random_uuid(),:'actor',id,'ROLE_CHANGED',role,:'desired',:'reason' FROM changed RETURNING target_user_id,new_role;
COMMIT;
'''
subprocess.run(['psql','-X','-h',url.hostname,'-p',str(url.port or 5432),'-U',env['ATLAS_MIGRATION_USERNAME'],'-d',url.path.lstrip('/')],input=sql,text=True,env=env,check=True)
print('Only an existing verified user can change. If no returned row, nothing changed (including last ADMIN protection).')
