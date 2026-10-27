#!/usr/bin/env python3
"""Separate API runtime from operator/migration credentials. Root-only --apply; reversible.
Uses the existing dedicated API PostgreSQL cluster on 55432, never the game database.
"""
import argparse,datetime,json,os,pathlib,pwd,shutil,subprocess,sys,time,urllib.request
ROOT=pathlib.Path('/home/somente/dev/atlas/atlas-api');CONFIG=pathlib.Path('/etc/atlas-api/runtime.env');OP='somente'
def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def values():
 result={}
 for line in (ROOT/'.env').read_text().splitlines():
  if line.strip() and not line.lstrip().startswith('#'):
   k,sep,v=line.partition('=')
   if not sep or '\n' in v or '\x00' in v:raise SystemExit('Invalid private configuration')
   result[k]=v
 return result
def preflight():
 v=values()
 if v.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local':raise SystemExit('Unexpected database: refusing')
 jar=ROOT/v['ATLAS_API_JAR']
 if jar.name!='atlas-api-0.8.0.jar' or not jar.is_file():raise SystemExit('Publish and verify API 0.8.0 first')
 if any(pathlib.Path('/etc/systemd/system',n).exists() for n in ('atlas-api.service','atlas-web-database.service')):raise SystemExit('Unexpected existing system unit; review manually')
 if CONFIG.exists():raise SystemExit('Isolation already configured; review rather than overwrite')
 if not (ROOT/'.runtime/postgres/PG_VERSION').is_file():raise SystemExit('Dedicated API cluster missing')
 print('Preflight OK: API dedicated UID, runtime-only secrets, read-only application, dedicated database service.')
 print('This restarts only the site API and its gateways, not Minecraft. Automatic rollback on failed health check.')
 return v,jar
def apply():
 if os.geteuid()!=0:raise SystemExit('Run with sudo and --apply')
 v,jar=preflight();operator=pwd.getpwnam(OP);uid=operator.pw_uid
 env=os.environ.copy();env.update(XDG_RUNTIME_DIR=f'/run/user/{uid}',DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{uid}/bus')
 def user(*args):return run('runuser','-u',OP,'--','env',f'XDG_RUNTIME_DIR=/run/user/{uid}',f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus','systemctl','--user',*args)
 # This read-only check prevents running an unverified/incomplete database migration during isolation.
 pg_env=os.environ.copy();pg_env['PGPASSWORD']=v['ATLAS_BOOTSTRAP_PASSWORD']
 result=subprocess.check_output(['/usr/lib/postgresql/18/bin/psql','-X','-h','127.0.0.1','-p','55432','-U','atlas_api_bootstrap','-d','atlas_api_local','-Atc','SELECT schema_generation FROM atlas_web.system_metadata WHERE id=1'],env=pg_env,text=True)
 if result.strip()!='12':raise SystemExit('Migration 12 must already be verified')
 try:api_user=pwd.getpwnam('atlas-api')
 except KeyError:run('useradd','--system','--no-create-home','--home-dir','/var/lib/atlas-api','--shell','/usr/sbin/nologin','atlas-api');api_user=pwd.getpwnam('atlas-api')
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=pathlib.Path('/var/backups/atlas-security')/('api-'+stamp);backup.mkdir(parents=True,mode=0o700)
 user_dir=pathlib.Path('/home/somente/.config/systemd/user');saved={}
 for path in user_dir.glob('*.service'):
  text=path.read_text()
  if 'atlas-api.service' in text and path.name!='atlas-api.service':
   saved[str(path)]=text
   text='\n'.join(line.replace('atlas-api.service','').rstrip() if line.startswith(('After=','Requires=','Wants=')) else line for line in text.splitlines())+'\n';path.write_text(text);os.chown(path,uid,operator.pw_gid)
 (backup/'user-units.json').write_text(json.dumps(saved));(backup/'user-units.json').chmod(0o600)
 destination=pathlib.Path('/opt/atlas-api');destination.mkdir(mode=0o755,exist_ok=True);shutil.copy2(jar,destination/jar.name);os.chmod(destination/jar.name,0o644)
 CONFIG.parent.mkdir(mode=0o700,exist_ok=True)
 excluded={'SPRING_CONFIG_ADDITIONAL_LOCATION','ATLAS_BOOTSTRAP_PASSWORD','ATLAS_MIGRATION_PASSWORD','ATLAS_MIGRATION_USERNAME','ATLAS_API_JAR','ATLAS_PG_BIN'}
 runtime={k:value for k,value in v.items() if k not in excluded}
 runtime.update(SPRING_FLYWAY_ENABLED='false',ATLAS_MIGRATION_USERNAME='disabled',ATLAS_MIGRATION_PASSWORD='disabled',ATLAS_LOCAL_MAIL_DIRECTORY='/var/lib/atlas-api/mail')
 CONFIG.touch(mode=0o600);CONFIG.write_text('\n'.join(k+'='+json.dumps(value,ensure_ascii=False) for k,value in runtime.items())+'\n');CONFIG.chmod(0o600)
 state=pathlib.Path('/var/lib/atlas-api');state.mkdir(mode=0o700,exist_ok=True);os.chown(state,api_user.pw_uid,api_user.pw_gid)
 pg_unit=pathlib.Path('/etc/systemd/system/atlas-web-database.service');api_unit=pathlib.Path('/etc/systemd/system/atlas-api.service')
 if pg_unit.exists() or api_unit.exists():raise SystemExit('Unexpected existing system service; review manually')
 pg_unit.write_text('''[Unit]
Description=Atlas dedicated website database
After=network.target
[Service]
Type=forking
User=somente
UMask=0077
NoNewPrivileges=true
ExecStart=/usr/lib/postgresql/18/bin/pg_ctl -D /home/somente/dev/atlas/atlas-api/.runtime/postgres -l /home/somente/dev/atlas/atlas-api/.runtime/postgres.log -o "-p 55432 -h 127.0.0.1 -k /home/somente/dev/atlas/atlas-api/.runtime" -w start
ExecStop=/usr/lib/postgresql/18/bin/pg_ctl -D /home/somente/dev/atlas/atlas-api/.runtime/postgres -m fast -w stop
PIDFile=/home/somente/dev/atlas/atlas-api/.runtime/postgres/postmaster.pid
TimeoutSec=60
[Install]
WantedBy=multi-user.target
''')
 api_unit.write_text('''[Unit]
Description=Atlas website API isolated runtime
After=network.target atlas-web-database.service
Requires=atlas-web-database.service
[Service]
User=atlas-api
Group=atlas-api
WorkingDirectory=/var/lib/atlas-api
EnvironmentFile=/etc/atlas-api/runtime.env
ExecStart=/usr/bin/java -jar /opt/atlas-api/atlas-api-0.8.0.jar
Restart=on-failure
RestartSec=5
TimeoutStopSec=40
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/atlas-api
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
LimitCORE=0
[Install]
WantedBy=multi-user.target
''')
 rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/python3
import json,os,pathlib,pwd,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
def run(*args):subprocess.run(args,check=True)
run('systemctl','disable','--now','atlas-api.service','atlas-web-database.service')
for name in ['atlas-api.service','atlas-web-database.service']:pathlib.Path('/etc/systemd/system',name).unlink(missing_ok=True)
for name,text in json.loads(pathlib.Path(__file__).with_name('user-units.json').read_text()).items():pathlib.Path(name).write_text(text)
pathlib.Path('/home/somente/dev/atlas/atlas-api/.runtime/isolated-api').unlink(missing_ok=True)
pathlib.Path('/etc/atlas-api/runtime.env').unlink(missing_ok=True)
run('systemctl','daemon-reload')
u=pwd.getpwnam('somente')
def user(*args):run('runuser','-u','somente','--','env',f'XDG_RUNTIME_DIR=/run/user/{u.pw_uid}',f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{u.pw_uid}/bus','systemctl','--user',*args)
user('daemon-reload');user('enable','--now','atlas-api.service');user('restart','atlas-api-preview.service','atlas-api-core-tls.service')
''');rollback.chmod(0o700)
 try:
  user('daemon-reload');user('disable','--now','atlas-api.service')
  # Legacy launcher may have inherited an already-running dedicated PG cluster.
  status=subprocess.run(['runuser','-u',OP,'--','/usr/lib/postgresql/18/bin/pg_ctl','-D',str(ROOT/'.runtime/postgres'),'status'],stdout=subprocess.DEVNULL)
  if status.returncode==0:run('runuser','-u',OP,'--','/usr/lib/postgresql/18/bin/pg_ctl','-D',str(ROOT/'.runtime/postgres'),'-m','fast','-w','stop',stdout=subprocess.DEVNULL)
  run('systemctl','daemon-reload');run('systemctl','enable','--now','atlas-web-database.service','atlas-api.service')
  ready=False
  for _ in range(60):
   try:
    with urllib.request.urlopen('http://127.0.0.1:8080/actuator/health/readiness',timeout=2) as response:
     if json.load(response).get('status')=='UP':ready=True;break
   except Exception:pass
   time.sleep(1)
  if not ready:raise RuntimeError('API readiness failed')
  if subprocess.run(['runuser','-u','atlas-api','--','test','-r',str(ROOT/'.env')]).returncode==0:raise RuntimeError('Operator credentials still readable')
  (ROOT/'.runtime/isolated-api').touch(mode=0o600)
  user('restart','atlas-api-preview.service','atlas-api-core-tls.service')
 except Exception:
  print('Isolation failed; restoring previous API service.',file=sys.stderr);run('python3',str(rollback));raise
 print('API isolated; runtime has no bootstrap/migrator credentials. Rollback:',rollback)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if args.apply:apply()
 else:preflight()
