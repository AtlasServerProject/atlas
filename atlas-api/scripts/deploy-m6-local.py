#!/usr/bin/env python3
"""Install verified M6 with private API/Core backups, keeping sales closed."""
from pathlib import Path
import datetime,json,os,re,shutil,subprocess,time,urllib.request
root=Path(__file__).resolve().parents[2];api=root/'atlas-api';core=root/'atlas-core';server=Path('/opt/atlas/server/fabric');runtime=api/'.runtime'
jar=api/'target/atlas-api-0.6.0.jar';corejar=runtime/'core-m6-build/build/libs/atlas-core-1.30.0.jar'
if not jar.is_file() or not corejar.is_file():raise SystemExit('Build and verify API/Core first.')
v=dict(l.split('=',1) for l in (api/'.env').read_text().splitlines() if '=' in l and not l.startswith('#'))
if v.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local' or v.get('ATLAS_SALES_ENABLED')!='false':raise SystemExit('Unexpected environment; sales must remain closed.')
game=dict(re.findall(r'public static final String (\w+) = "([^"]*)";', (core/'src/main/java/io/atlas/modules/database/DatabaseConfig.java').read_text()))
backup=runtime/'backups'/('before-m6-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
shutil.copy2(api/'.env',backup/'api.env');(backup/'api.env').chmod(0o600)
old=api/v['ATLAS_API_JAR'];shutil.copy2(old,backup/'api-previous.jar')
for mod in (server/'mods').glob('atlas-core-*.jar'):shutil.copy2(mod,backup/mod.name)
for name in ['atlas-vip.properties','atlas-core-api.crt']:
 if (server/'config'/name).exists():shutil.copy2(server/'config'/name,backup/name)
def dump(name,port,user,password,db):
 target=backup/name;subprocess.run(['/usr/lib/postgresql/18/bin/pg_dump','-h','127.0.0.1','-p',str(port),'-U',user,'-d',db,'-Fc','-f',str(target)],env={**os.environ,'PGPASSWORD':password},check=True,stderr=subprocess.DEVNULL);target.chmod(0o600)
dump('api.dump',55432,'atlas_api_bootstrap',v['ATLAS_BOOTSTRAP_PASSWORD'],'atlas_api_local');dump('core.dump',5432,game['USER'],game['PASSWORD'],game['DATABASE'])
query='BEGIN;\n'+(root/'database/migrations/034_commercial_vip_ledger.sql').read_text()+'\nCOMMIT;'
subprocess.run(['psql','-X','-h',game['HOST'],'-p','5432','-U',game['USER'],'-d',game['DATABASE'],'-v','ON_ERROR_STOP=1'],input=query,text=True,env={**os.environ,'PGPASSWORD':game['PASSWORD']},check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
cert=runtime/'core-tls.crt';key=runtime/'core-tls.key'
if not cert.exists():
 subprocess.run(['openssl','req','-x509','-newkey','rsa:3072','-sha256','-nodes','-days','365','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1','-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);key.chmod(0o600);cert.chmod(0o600)
units=Path.home()/'.config/systemd/user';shutil.copy2(root/'infra/templates/atlas-api-core-tls.service',units/'atlas-api-core-tls.service')
release=runtime/'releases/atlas-api-0.6.0.jar';shutil.copy2(jar,release);release.chmod(0o600)
updates={'ATLAS_API_JAR':'.runtime/releases/atlas-api-0.6.0.jar','ATLAS_DELIVERY_ENABLED':'true','ATLAS_DELIVERY_MODE':'production','ATLAS_SALES_ENABLED':'false'}
lines=(api/'.env').read_text().splitlines()
for k,value in updates.items():lines=[l for l in lines if not l.startswith(k+'=')];lines.append(k+'='+value)
(api/'.env').write_text('\n'.join(lines)+'\n');(api/'.env').chmod(0o600)
subprocess.run(['systemctl','--user','daemon-reload'],check=True);subprocess.run(['systemctl','--user','restart','atlas-api.service'],check=True)
for _ in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/system',timeout=2) as r:info=json.load(r)
  if info.get('version')=='0.6.0' and info.get('schemaGeneration')==8:break
 except (OSError,ValueError):pass
 time.sleep(1)
else:raise SystemExit('API not ready; private backup retained. Do not undo Flyway history.')
subprocess.run(['systemctl','--user','enable','--now','atlas-api-core-tls.service'],check=True)
config=server/'config/atlas-vip.properties';config.write_text('api-url=https://127.0.0.1:4202\nkey='+v['ATLAS_CORE_KEY']+'\ntrusted-certificate='+str(server/'config/atlas-core-api.crt')+'\n');config.chmod(0o600);shutil.copy2(cert,server/'config/atlas-core-api.crt');(server/'config/atlas-core-api.crt').chmod(0o644)
# Backup exists before touching mods; preserve a single active Core jar.
staged=server/'mods/atlas-core-1.30.0.jar.pending';shutil.copy2(corejar,staged);staged.replace(server/'mods/atlas-core-1.30.0.jar')
for old in (server/'mods').glob('atlas-core-*.jar'):
 if old.name!='atlas-core-1.30.0.jar':old.unlink()
print('API 0.6.0/schema 8 installed, private HTTPS active, Core 1.30.0 copied with backups. Restart atlas and inspect startup logs. Sales remain closed.',flush=True)
