#!/usr/bin/env python3
"""Persistent local development using an owned native PostgreSQL cluster; never uses the game DB."""
import os
from pathlib import Path
import re
import signal
import subprocess

root = Path(__file__).resolve().parents[1]
local = root / '.env'
if not local.is_file():
    subprocess.run(['python3', str(root/'scripts/init-local-env.py')], check=True)
env = os.environ.copy()
for line in local.read_text().splitlines():
    if not line.strip() or line.lstrip().startswith('#'): continue
    key, sep, value = line.partition('=')
    if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*', key): raise SystemExit('Invalid plain local environment file.')
    env.setdefault(key, value)
if env.get('ATLAS_DB_URL') != 'jdbc:postgresql://127.0.0.1:55432/atlas_api_local' or env.get('SPRING_PROFILES_ACTIVE') not in {'local', 'local,preview'}:
    raise SystemExit('Native development requires the dedicated loopback local database and local profile.')
for key in ['ATLAS_BOOTSTRAP_PASSWORD','ATLAS_DB_PASSWORD','ATLAS_MIGRATION_PASSWORD','ATLAS_MAIL_ENCRYPTION_KEY']:
    if not env.get(key): raise SystemExit(f'Configure {key} securely in the ignored local environment.')
pg_bin = Path(env.get('ATLAS_PG_BIN','/usr/lib/postgresql/18/bin'))
for name in ['initdb','pg_ctl','psql']:
    if not (pg_bin/name).is_file(): raise SystemExit('PostgreSQL 18 tools are required for native local development.')
jar = root/env.get('ATLAS_API_JAR','target/atlas-api-0.5.0.jar')
if not jar.is_file(): raise SystemExit('Build and verify the API before starting local development.')
runtime = root/'.runtime'
runtime.mkdir(mode=0o700,exist_ok=True);runtime.chmod(0o700)
data = runtime/'postgres'
password_file = runtime/'init-password'
started = False
api = None

def stop_signal(signum, frame): raise KeyboardInterrupt
signal.signal(signal.SIGTERM,stop_signal)

def sql(query, database='atlas_api_local'):
    query_env = env.copy();query_env['PGPASSWORD']=env['ATLAS_BOOTSTRAP_PASSWORD']
    return subprocess.run([str(pg_bin/'psql'),'-X','-h','127.0.0.1','-p','55432','-U','atlas_api_bootstrap',
                           '-d',database,'-v','ON_ERROR_STOP=1','-At'],input=query,text=True,env=query_env,
                          stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout.strip()
try:
    if not (data/'PG_VERSION').is_file():
        password_file.touch(mode=0o600,exist_ok=False);password_file.write_text(env['ATLAS_BOOTSTRAP_PASSWORD'])
        subprocess.run([str(pg_bin/'initdb'),'-D',str(data),'-U','atlas_api_bootstrap','--auth=scram-sha-256',
                        '--pwfile',str(password_file),'--encoding=UTF8','--no-locale'],check=True,stdout=subprocess.DEVNULL)
        password_file.unlink()
    elif (data/'PG_VERSION').read_text().strip() != '18':
        raise SystemExit('Existing cluster requires a PostgreSQL upgrade; no automatic overwrite.')
    status = subprocess.run([str(pg_bin/'pg_ctl'),'-D',str(data),'status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if status.returncode != 0:
        subprocess.run([str(pg_bin/'pg_ctl'),'-D',str(data),'-w','start','-l',str(runtime/'postgres.log'),
                        '-o',f'-p 55432 -h 127.0.0.1 -k {runtime}'],check=True,stdout=subprocess.DEVNULL)
        started = True
    sql("SELECT 'CREATE DATABASE atlas_api_local' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='atlas_api_local') \\gexec\n",'postgres')
    if sql("SELECT count(*) FROM pg_namespace WHERE nspname='atlas_web'") == '0':
        sql('BEGIN;\n'+(root/'infra/postgres/provision.sql').read_text()+'\nCOMMIT;\n')
    print('Persistent Atlas API starting on loopback with dedicated database.',flush=True)
    api = subprocess.Popen(['java','-jar',str(jar)],cwd=root,env=env)
    result = api.wait()
    if result: raise SystemExit(result)
except KeyboardInterrupt:
    pass
finally:
    if api and api.poll() is None:
        api.terminate()
        try: api.wait(timeout=25)
        except subprocess.TimeoutExpired: api.kill();api.wait()
    if started:
        subprocess.run([str(pg_bin/'pg_ctl'),'-D',str(data),'-w','stop','-m','fast'],stdout=subprocess.DEVNULL,check=True)
    password_file.unlink(missing_ok=True)
