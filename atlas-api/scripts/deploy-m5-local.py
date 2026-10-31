#!/usr/bin/env python3
"""Install verified M5 API with a private backup. Keep payments/sales disabled."""
from pathlib import Path
import datetime, json, os, shutil, subprocess, time, urllib.request
api=Path(__file__).resolve().parents[1]
jar=api/'target/atlas-api-0.5.0.jar'
if not jar.is_file(): raise SystemExit('Build and validate M5 before installing.')
values={k:v for line in (api/'.env').read_text().splitlines() if not line.startswith('#') for k,sep,v in [line.partition('=')] if sep}
if values.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local': raise SystemExit('Unexpected API environment.')
backup=api/'.runtime/backups'/('before-m5-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(mode=0o700)
shutil.copy2(api/'.env',backup/'api.env');(backup/'api.env').chmod(0o600)
previous=api/values.get('ATLAS_API_JAR','target/atlas-api-0.4.2.jar')
if previous.is_file():shutil.copy2(previous,backup/'api-previous.jar');(backup/'api-previous.jar').chmod(0o600)
subprocess.run(['/usr/lib/postgresql/18/bin/pg_dump','-h','127.0.0.1','-p','55432','-U','atlas_api_bootstrap','-d','atlas_api_local','-Fc','-f',str(backup/'api.dump')],env={**os.environ,'PGPASSWORD':values['ATLAS_BOOTSTRAP_PASSWORD']},check=True,stderr=subprocess.DEVNULL)
(backup/'api.dump').chmod(0o600)
release=api/'.runtime/releases/atlas-api-0.5.0.jar';shutil.copy2(jar,release);release.chmod(0o600)
updates={'ATLAS_API_JAR':'.runtime/releases/atlas-api-0.5.0.jar','ATLAS_SALES_ENABLED':'false','ATLAS_PAYMENT_ENABLED':'false','ATLAS_MP_MODE':'test'}
lines=(api/'.env').read_text().splitlines()
for field,value in updates.items():lines=[line for line in lines if not line.startswith(field+'=')];lines.append(field+'='+value)
for field,value in {'ATLAS_MP_ACCESS_TOKEN':'','ATLAS_MP_WEBHOOK_SECRET':'','ATLAS_MP_COLLECTOR_ID':'','ATLAS_MP_NOTIFICATION_URL':'https://atlas-cobblemon.netlify.app/api/v1/webhooks/mercadopago'}.items():
 if field not in values:lines.append(field+'='+value)
(api/'.env').write_text('\n'.join(lines)+'\n');(api/'.env').chmod(0o600)
subprocess.run(['systemctl','--user','restart','atlas-api'],check=True)
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8080/api/v1/system',timeout=2) as response:info=json.load(response)
  if info.get('version')=='0.5.0' and info.get('schemaGeneration')==7:break
 except (OSError,ValueError):pass
 time.sleep(1)
else:raise SystemExit('M5 failed to become ready; backup preserved. Restore api.env/JAR before retrying; do not modify migrations.')
print('M5 API installed; schema 7 applied; private backup saved. Payments and sales remain disabled.')
