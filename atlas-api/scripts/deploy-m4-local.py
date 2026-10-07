#!/usr/bin/env python3
"""Install validated M4 on this VM, preserving private DB/JAR backups. Never prints credentials."""
import os,re,subprocess,shutil,secrets,datetime,signal,getpass,time,json,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[2];api=root/'atlas-api';core=root/'atlas-core';server=Path('/opt/atlas/server/fabric')
if not (api/'target/atlas-api-0.4.2.jar').is_file() or not (core/'build/libs/atlas-core-1.29.25.jar').is_file():raise SystemExit('Build and validate API/Core before installing.')
owner=subprocess.check_output(['systemctl','show','atlas','--property=User','--value'],text=True).strip()
restart=subprocess.check_output(['systemctl','show','atlas','--property=Restart','--value'],text=True).strip()
if owner!=getpass.getuser():raise SystemExit('Core belongs to another user; restart is required.')
if restart!='always':raise SystemExit('Core installed; service requires an explicit restart.')
source=(core/'src/main/java/io/atlas/modules/database/DatabaseConfig.java').read_text();game_password=re.search(r'PASSWORD\s*=\s*"([^"]+)"',source).group(1)
values={k:v for l in (api/'.env').read_text().splitlines() if not l.startswith('#') for k,sep,v in [l.partition('=')] if sep}
if values.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local':raise SystemExit('Unexpected API environment; no changes applied.')
backup=api/'.runtime/backups'/('before-m4-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
for name,port,user,database,password in [('api',55432,'atlas_api_bootstrap','atlas_api_local',values['ATLAS_BOOTSTRAP_PASSWORD']),('core',5432,'atlas_app','atlas',game_password)]:
 dest=backup/(name+'.dump')
 subprocess.run(['/usr/lib/postgresql/18/bin/pg_dump','-h','127.0.0.1','-p',str(port),'-U',user,'-d',database,'-Fc','-f',str(dest)],env={**os.environ,'PGPASSWORD':password},check=True,stderr=subprocess.DEVNULL)
 dest.chmod(0o600)
installed=list((server/'mods').glob('atlas-core*.jar'))
if len(installed)!=1:raise SystemExit('Expected exactly one installed Core; backups preserved and installation stopped.')
shutil.copy2(installed[0],backup/'atlas-core-previous.jar');(backup/'atlas-core-previous.jar').chmod(0o600)
config=server/'config/atlas-site.properties'
if config.exists():shutil.copy2(config,backup/'atlas-site.properties');(backup/'atlas-site.properties').chmod(0o600)
shutil.copy2(api/'.env',backup/'api.env');(backup/'api.env').chmod(0o600)
query='BEGIN;\n'+(root/'database/migrations/033_site_identities.sql').read_text()+'\nCOMMIT;\n'
subprocess.run(['psql','-X','-h','127.0.0.1','-p','5432','-U','atlas_app','-d','atlas','-v','ON_ERROR_STOP=1','-q'],input=query,text=True,env={**os.environ,'PGPASSWORD':game_password},check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
key=values.get('ATLAS_CORE_KEY') or secrets.token_urlsafe(32)
if len(key)<43:raise SystemExit('Existing Core key is invalid; backups preserved.')
config.write_text('api-url=http://127.0.0.1:8080\nkey='+key+'\n');config.chmod(0o600)
release=api/'.runtime/releases/atlas-api-0.4.2.jar';shutil.copy2(api/'target/atlas-api-0.4.2.jar',release);release.chmod(0o600)
lines=(api/'.env').read_text().splitlines()
for field,value in {'ATLAS_CORE_KEY':key,'ATLAS_SALES_ENABLED':'false','ATLAS_API_JAR':'.runtime/releases/atlas-api-0.4.2.jar'}.items():
 lines=[l for l in lines if not l.startswith(field+'=')];lines.append(field+'='+value)
(api/'.env').write_text('\n'.join(lines)+'\n');(api/'.env').chmod(0o600)
subprocess.run(['systemctl','--user','restart','atlas-api','atlas-api-preview','atlas-api-tunnel'],check=True)
for attempt in range(60):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/system',timeout=2) as response: info=json.load(response)
  if info.get('version')=='0.4.2' and info.get('schemaGeneration')==6: break
 except (OSError,ValueError): pass
 time.sleep(1)
else: raise SystemExit('API did not become ready. Core remains unchanged; restore the private api.env backup if needed.')
# Atomic replacement; the only installed Core path is retained.
staged=installed[0].with_suffix('.jar.next');shutil.copy2(core/'build/libs/atlas-core-1.29.25.jar',staged);staged.replace(installed[0])
# Java runs as this owner and handles SIGTERM through the Minecraft graceful shutdown hook.
# The system service's existing Restart=always restarts it; no new privilege policy is introduced.
pid=int(subprocess.check_output(['systemctl','show','atlas','--property=MainPID','--value'],text=True).strip())
if pid<=1 or Path('/proc/'+str(pid)).stat().st_uid!=os.getuid():raise SystemExit('Core installed; owned live process was not found for graceful restart.')
os.kill(pid,signal.SIGTERM)
print('M4 installed with private backups; API restarted and graceful Core restart requested.')
