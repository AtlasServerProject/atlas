#!/usr/bin/env python3
"""Activate the prepared permanent tunnel only after account/DNS setup. No secrets printed."""
from pathlib import Path
import argparse, datetime, json, os, re, shutil, subprocess, time, urllib.request
from urllib.parse import urlsplit
root=Path(__file__).resolve().parents[2];api=root/'atlas-api';runtime=api/'.runtime'
parser=argparse.ArgumentParser()
parser.add_argument('--site-url',default='https://atlascobblemon.com.br')
args=parser.parse_args();url=urlsplit(args.site_url)
if url.scheme!='https' or url.username or url.password or url.port or url.path not in ('','/') or url.query or url.fragment or not (url.hostname in {'atlascobblemon.com.br','www.atlascobblemon.com.br'} or re.fullmatch(r'[a-z0-9-]+\.pages\.dev',url.hostname or '')):raise SystemExit('Use the actual Atlas HTTPS domain or verified Pages production hostname.')
site_url='https://'+url.hostname
private=runtime/'cloudflare-tunnel.token'
if not private.is_file() or not private.read_text().strip():raise SystemExit('Configure the permanent tunnel token in the private runtime file first. Never send it in chat.')
private.chmod(0o600)
values={k:v for line in (api/'.env').read_text().splitlines() if not line.startswith('#') for k,sep,v in [line.partition('=')] if sep}
if values.get('ATLAS_DB_URL')!='jdbc:postgresql://127.0.0.1:55432/atlas_api_local':raise SystemExit('Unexpected API environment.')
config=runtime/'cloudflare-web.yml'
location='file:'+str(config)
if values.get('SPRING_CONFIG_ADDITIONAL_LOCATION') not in (None,'',location):raise SystemExit('An existing external Spring configuration requires review before activation.')
backup=runtime/'backups'/('before-cloudflare-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(mode=0o700)
shutil.copy2(api/'.env',backup/'api.env');(backup/'api.env').chmod(0o600)
if config.exists():shutil.copy2(config,backup/'cloudflare-web.yml');(backup/'cloudflare-web.yml').chmod(0o600)
origins=list(dict.fromkeys([site_url,'https://atlascobblemon.com.br','https://www.atlascobblemon.com.br','https://atlas-cobblemon.netlify.app']))
config.write_text('atlas:\n  mail:\n    web-url: '+json.dumps(site_url)+'\n  cors:\n    allowed-origins:\n'+''.join('      - '+json.dumps(origin)+'\n' for origin in origins));config.chmod(0o600)
updates={'SPRING_CONFIG_ADDITIONAL_LOCATION':location,'ATLAS_WEB_URL':site_url,'ATLAS_MP_NOTIFICATION_URL':site_url+'/api/v1/webhooks/mercadopago'}
lines=(api/'.env').read_text().splitlines()
for field,value in updates.items():lines=[line for line in lines if not line.startswith(field+'=')];lines.append(field+'='+value)
(api/'.env').write_text('\n'.join(lines)+'\n');(api/'.env').chmod(0o600)
units=Path.home()/'.config/systemd/user';unit=units/'atlas-api-cloudflare.service';units.mkdir(parents=True,exist_ok=True)
if unit.exists():shutil.copy2(unit,backup/'atlas-api-cloudflare.service')
shutil.copy2(root/'infra/templates/atlas-api-cloudflare.service',unit)
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','restart','atlas-api'],check=True)
subprocess.run(['systemctl','--user','enable','--now','atlas-api-cloudflare.service'],check=True)
# DNS/account configuration is external. Leave old tunnel intact on failed validation.
for attempt in range(18):
 try:
  with urllib.request.urlopen(site_url+'/api/v1/system',timeout=2) as response:data=json.load(response)
  if data.get('application')=='atlas-api' and data.get('version')=='0.5.0':break
 except (OSError,ValueError):pass
 time.sleep(1)
else:raise SystemExit('Public routing is not ready. Private backup preserved; old tunnel remains active. Check DNS, Pages and the permanent tunnel route before retrying.')
subprocess.run(['systemctl','--user','disable','--now','atlas-api-tunnel-sync.timer','atlas-api-tunnel.service'],check=True)
print('Cloudflare routing activated and verified. Mail links/webhook URL updated. API data, sales flags and credentials preserved.')
