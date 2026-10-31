#!/usr/bin/env python3
"""Deploy verified purchase mailbox. Production and sandbox remain separate."""
from pathlib import Path
import os,re,json,shutil,subprocess,time,datetime,urllib.request
root=Path(__file__).resolve().parents[2];api=root/'atlas-api';runtime=api/'.runtime';main=Path('/opt/atlas/server/fabric');dev=Path.home()/'.local/share/atlas-dev/fabric';sandbox=runtime/'payment-sandbox';pg=Path('/usr/lib/postgresql/18/bin')
jar=api/'target/atlas-api-0.7.0.jar';core=runtime/'mailbox-core-build/build/libs/atlas-core-1.30.11.jar';assert jar.is_file() and core.is_file()
v=dict(l.split('=',1) for l in (api/'.env').read_text().splitlines() if '=' in l and not l.startswith('#'));assert v['ATLAS_DB_URL']=='jdbc:postgresql://127.0.0.1:55432/atlas_api_local' and v['ATLAS_SALES_ENABLED']=='false'
state=json.loads((sandbox/'state.json').read_text());test=json.loads((sandbox/'process-env.json').read_text());assert test['ATLAS_MP_MODE']=='test' and test['ATLAS_DB_URL']==f"jdbc:postgresql://127.0.0.1:{state['db_port']}/postgres" and state['db_port'] not in [5432,55432,25432]
backup=runtime/'backups'/('before-mailbox-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
for source,name in [(api/'.env','api.env'),(sandbox/'process-env.json','sandbox-env.json'),(sandbox/'state.json','sandbox-state.json'),(api/v['ATLAS_API_JAR'],'api-previous.jar')]:shutil.copy2(source,backup/name);(backup/name).chmod(0o600)
def run(cmd,**kwargs):return subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**kwargs)
def dump(port,user,password,database,name):run([str(pg/'pg_dump'),'-h','127.0.0.1','-p',str(port),'-U',user,'-d',database,'-Fc','-f',str(backup/name)],env={**os.environ,'PGPASSWORD':password});(backup/name).chmod(0o600)
dump(55432,'atlas_api_bootstrap',v['ATLAS_BOOTSTRAP_PASSWORD'],'atlas_api_local','api.dump');dump(state['db_port'],'atlas_api_bootstrap',test['ATLAS_BOOTSTRAP_PASSWORD'],'postgres','sandbox.dump')
def properties(server):
 source=root/'atlas-core/src/main/java/io/atlas/modules/database/DatabaseConfig.java'
 config=dict(re.findall(r'getProperty\("(\w+)", "([^"\n]*)"\)',source.read_text()))
 file=server/'config/atlas-database.properties'
 if file.exists():config.update(dict(l.split('=',1) for l in file.read_text().splitlines() if '=' in l and not l.startswith('#')))
 return config
for server,label in [(main,'main'),(dev,'dev')]:
 config=properties(server);assert (config['database']=='atlas_dev' and config['port']=='25432') if label=='dev' else (config['database']=='atlas' and config['port']=='5432')
 dump(config['port'],config['user'],config['password'],config['database'],label+'-core.dump')
 sql=(root/'database/migrations/036_vip_commands.sql').read_text().replace('TO atlas_app','TO '+config['user'])
 migration_user='atlas_dev_admin' if label=='dev' else config['user']
 migration_password=(dev.parent/'database-secrets').read_text().splitlines()[0] if label=='dev' else config['password']
 run([str(pg/'psql'),'-X','-h','127.0.0.1','-p',config['port'],'-U',migration_user,'-d',config['database'],'-v','ON_ERROR_STOP=1'],input='BEGIN;'+sql+'COMMIT;',text=True,env={**os.environ,'PGPASSWORD':migration_password})
 for old in (server/'mods').glob('atlas-core*.jar'):shutil.copy2(old,backup/(label+'-'+old.name))
 for name in ['atlas-vip.properties','atlas-core-api.crt']:
  if (server/'config'/name).exists():shutil.copy2(server/'config'/name,backup/(label+'-'+name))
release=runtime/'releases/atlas-api-0.7.0.jar';release.parent.mkdir(exist_ok=True);shutil.copy2(jar,release)
text=(api/'.env').read_text();text=re.sub(r'^ATLAS_API_JAR=.*$', 'ATLAS_API_JAR=.runtime/releases/atlas-api-0.7.0.jar',text,flags=re.M);(api/'.env').write_text(text);(api/'.env').chmod(0o600)
run(['systemctl','--user','restart','atlas-api'])
for i in range(90):
 try:
  data=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/system',timeout=2))
  if data['version']=='0.7.0' and data['schemaGeneration']==11:break
 except Exception:pass
 time.sleep(1)
else:raise SystemExit('API readiness pending; private backup preserved.')
# Stop only the verified old sandbox process; keep its data and orders.
proc=Path('/proc')/str(state['api_pid'])
if proc.exists():
 current=dict(s.split('=',1) for s in (proc/'environ').read_text().split('\0') if '=' in s);assert current.get('ATLAS_DB_URL')==test['ATLAS_DB_URL'];os.kill(state['api_pid'],15)
run([str(pg/'pg_ctl'),'-D',str(sandbox/'data'),'-w','stop','-m','fast'])
test.update({'ATLAS_DELIVERY_ENABLED':'true','ATLAS_DELIVERY_MODE':'test'});(sandbox/'process-env.json').write_text(json.dumps(test));(sandbox/'process-env.json').chmod(0o600)
wrapper=sandbox/'run-api.py';wrapper.write_text("from pathlib import Path\nimport os,json\np=Path(__file__).parent\ne={**os.environ,**json.loads((p/'process-env.json').read_text())}\nos.execvpe('java',['java','-Xms64m','-Xmx256m','-jar',"+repr(str(release))+"],e)\n");wrapper.chmod(0o700)
units=Path.home()/'.config/systemd/user'
(units/'atlas-payment-sandbox-postgres.service').write_text(f"[Unit]\nDescription=Atlas payment sandbox PostgreSQL\n[Service]\nExecStart={pg}/postgres -D {sandbox/'data'} -p {state['db_port']} -h 127.0.0.1 -k {sandbox}\nRestart=on-failure\nKillSignal=SIGINT\nUMask=0077\n[Install]\nWantedBy=default.target\n")
(units/'atlas-payment-sandbox.service').write_text(f"[Unit]\nDescription=Atlas payment sandbox API\nRequires=atlas-payment-sandbox-postgres.service\nAfter=atlas-payment-sandbox-postgres.service\n[Service]\nWorkingDirectory={api}\nExecStart=/usr/bin/python3 {wrapper}\nRestart=on-failure\nUMask=0077\n[Install]\nWantedBy=default.target\n")
(units/'atlas-payment-sandbox-tls.service').write_text(f"[Unit]\nDescription=Private test-only Core purchase TLS\nRequires=atlas-payment-sandbox.service\nAfter=atlas-payment-sandbox.service\n[Service]\nEnvironment=ATLAS_CORE_TLS_PORT=4203\nEnvironment=ATLAS_CORE_TLS_UPSTREAM_PORT={state['api_port']}\nExecStart=/usr/bin/python3 {root/'infra/scripts/serve-core-tls.py'}\nRestart=on-failure\nUMask=0077\n[Install]\nWantedBy=default.target\n")
run(['systemctl','--user','daemon-reload']);run(['systemctl','--user','enable','--now','atlas-payment-sandbox-postgres','atlas-payment-sandbox','atlas-payment-sandbox-tls']);run(['systemctl','--user','restart','atlas-api-core-tls'])
for i in range(90):
 try:
  data=json.load(urllib.request.urlopen(f"http://127.0.0.1:{state['api_port']}/api/v1/system",timeout=2))
  if data['version']=='0.7.0' and data['schemaGeneration']==11:break
 except Exception:pass
 time.sleep(1)
else:raise SystemExit('Sandbox readiness pending.')
state['api_pid']=int(subprocess.check_output(['systemctl','--user','show','atlas-payment-sandbox','-p','MainPID','--value'],text=True));(sandbox/'state.json').write_text(json.dumps(state));(sandbox/'state.json').chmod(0o600)
shutil.copy2(runtime/'core-tls.crt',dev/'config/atlas-core-api.crt')
(dev/'config/atlas-vip.properties').write_text('api-url=https://127.0.0.1:4203\nkey='+test['ATLAS_CORE_KEY']+'\ntrusted-certificate=config/atlas-core-api.crt\n');(dev/'config/atlas-vip.properties').chmod(0o600)
for server in [main,dev]:
 shutil.copy2(core,server/'mods'/core.name)
 for old in (server/'mods').glob('atlas-core*.jar'):
  if old.name!=core.name:old.unlink()
print('PASS: API 0.7.0/schema 11 ready in production and isolated sandbox; both Core JARs installed; sales remain closed. Restart Minecraft instances to load Core 1.30.11.')
