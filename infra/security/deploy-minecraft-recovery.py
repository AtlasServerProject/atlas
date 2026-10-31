#!/usr/bin/env python3
"""Privileged Minecraft recovery API release and isolated migration.
Preserves the already-configured Google client and mail runtime.
"""
import argparse,datetime,hashlib,json,os,pathlib,re,shutil,subprocess,tempfile,time,urllib.request,zipfile
API=pathlib.Path('/home/somente/dev/atlas/atlas-api');ENV=pathlib.Path('/etc/atlas-api/runtime.env');JAR=API/'.runtime/releases/atlas-api-0.10.0.jar';DROP=pathlib.Path('/etc/systemd/system/atlas-api.service.d/80-release.conf')
def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def read_env(path):
 out={}
 for line in path.read_text().splitlines():
  if not line.strip() or line.lstrip().startswith('#'):continue
  k,sep,v=line.partition('=')
  if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*',k):raise SystemExit('Invalid environment file')
  out[k]=json.loads(v) if v.startswith('"') else v
 return out
def preflight():
 if not JAR.is_file():raise SystemExit('Build and stage API 0.10.0 first.')
 digest=hashlib.sha256(JAR.read_bytes()).hexdigest();expected=JAR.with_suffix('.jar.sha256').read_text().strip()
 if digest!=expected:raise SystemExit('Staged release checksum mismatch.')
 if subprocess.check_output(['systemctl','show','atlas-api.service','-p','User','--value'],text=True).strip()!='atlas-api':raise SystemExit('API isolation must already be active.')
 print('Verified API 0.10.0: Minecraft recovery email enrollment and password reset.')
 print('Apply backs up DB/config, runs only Flyway migrations, preserves service isolation and rolls back on failed health checks.')
 return digest
def apply():
 if os.geteuid()!=0:raise SystemExit('This isolated API deployment requires sudo.')
 digest=preflight();old=read_env(ENV);operator=read_env(API/'.env')
 client=old.get('ATLAS_GOOGLE_CLIENT_ID','')
 if not client:client=input('Client ID público do Google (termina em .apps.googleusercontent.com): ').strip()
 else:print('Keeping the Google web Client ID already configured.')
 if not re.fullmatch(r'[A-Za-z0-9-]+\.apps\.googleusercontent\.com',client):raise SystemExit('Invalid Google web Client ID; no changes made.')
 if old.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local' or old.get('SPRING_FLYWAY_ENABLED')!='false':raise SystemExit('Unexpected isolated runtime; refusing.')
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=pathlib.Path('/var/backups/atlas-security')/('google-'+stamp);backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(ENV,backup/'runtime.env');(backup/'runtime.env').chmod(0o600)
 previous_drop=DROP.read_text() if DROP.exists() else None
 (backup/'previous-release.json').write_text(json.dumps({'dropin':previous_drop,'sha256':digest},indent=2))
 pg_env=os.environ.copy();pg_env['PGPASSWORD']=operator['ATLAS_BOOTSTRAP_PASSWORD']
 run('/usr/lib/postgresql/18/bin/pg_dump','-h','127.0.0.1','-p','55432','-U','atlas_api_bootstrap','-d','atlas_api_local','-Fc','-f',str(backup/'api-database.dump'),env=pg_env,stdout=subprocess.DEVNULL)
 (backup/'api-database.dump').chmod(0o600)
 destination=pathlib.Path('/opt/atlas-api/atlas-api-0.10.0.jar');shutil.copy2(JAR,destination);destination.chmod(0o644)
 if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:raise SystemExit("Release changed while copying; rerun after staging finishes.")
 # A plain Java main runs Flyway only: no API, mail scheduler or payment/delivery jobs.
 with tempfile.TemporaryDirectory(prefix='atlas-schema-') as temporary:
  folder=pathlib.Path(temporary)
  with zipfile.ZipFile(destination) as archive:
   for entry in archive.infolist():
    if entry.is_dir():continue
    if entry.filename.startswith(('BOOT-INF/classes/','BOOT-INF/lib/')):
     relative=pathlib.PurePosixPath(entry.filename)
     if '..' in relative.parts or relative.is_absolute():raise SystemExit('Unsafe archive entry')
     target=folder.joinpath(*relative.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
  migration_env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'ATLAS_DB_URL':old['ATLAS_DB_URL'],'ATLAS_MIGRATION_USERNAME':operator['ATLAS_MIGRATION_USERNAME'],'ATLAS_MIGRATION_PASSWORD':operator['ATLAS_MIGRATION_PASSWORD']}
  with (backup/'migration.log').open('w') as log:
   run('/usr/bin/java','-cp',str(folder/'BOOT-INF/classes')+':'+str(folder/'BOOT-INF/lib/*'),'io.atlas.api.migration.SchemaMigrator',env=migration_env,stdout=log,stderr=log)
 (backup/'migration.log').chmod(0o600)
 new=dict(old);new.update(ATLAS_GOOGLE_ENABLED='true',ATLAS_GOOGLE_CLIENT_ID=client)
 ENV.write_text('\n'.join(k+'='+json.dumps(v,ensure_ascii=False) for k,v in new.items())+'\n');ENV.chmod(0o600)
 DROP.parent.mkdir(parents=True,exist_ok=True);DROP.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/java -jar /opt/atlas-api/atlas-api-0.10.0.jar\n')
 rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/python3
import json,os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent
shutil.copy2(p/'runtime.env','/etc/atlas-api/runtime.env')
drop=pathlib.Path('/etc/systemd/system/atlas-api.service.d/80-release.conf');old=json.loads((p/'previous-release.json').read_text())['dropin']
if old is None:drop.unlink(missing_ok=True)
else:drop.write_text(old)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','atlas-api.service'],check=True)
print('Previous API restored; additive schema migration retained, no order/account data deleted.')
''');rollback.chmod(0o700)
 try:
  run('systemctl','daemon-reload');run('systemctl','restart','atlas-api.service')
  ready=False
  for _ in range(60):
   try:
    with urllib.request.urlopen('http://127.0.0.1:8080/actuator/health/readiness',timeout=2) as r:healthy=json.load(r).get('status')=='UP'
    with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/system',timeout=2) as r:info=json.load(r)
    with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/auth/google/provider',timeout=2) as r:provider=json.load(r)
    if healthy and info.get('version')=='0.10.0' and info.get('schemaGeneration')==14 and provider.get('enabled') and provider.get('clientId')==client:ready=True;break
   except Exception:pass
   time.sleep(1)
  if not ready:raise RuntimeError('New API failed readiness/provider verification')
 except Exception:run('python3',str(rollback));raise
 print('API 0.10.0 ready, schema 14, Google configured. Minecraft email recovery endpoints configured; real player email confirmation still needs testing.')
 print('Isolation preserved. Rollback:',rollback)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if args.apply:apply()
 else:preflight()
