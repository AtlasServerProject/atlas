#!/usr/bin/env python3
"""Require the verified Atlas resource pack on login; no Core or world changes."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,urllib.request,uuid,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric')
def preflight():
 metadata=ROOT/'infra/resourcepacks/transparent-keys-release.json'
 if not metadata.exists():raise SystemExit('Transparent key textures are not ready; no changes made.')
 data=json.loads(metadata.read_text());pack=pathlib.Path(data['file'])
 if pack.parent!=ROOT/'infra/resourcepacks' or hashlib.sha256(pack.read_bytes()).hexdigest()!=data['sha256'] or hashlib.sha1(pack.read_bytes()).hexdigest()!=data['sha1']:raise SystemExit('Pack verification failed.')
 with zipfile.ZipFile(pack) as z:
  if z.testzip() or json.loads(z.read('pack.mcmeta'))['pack']['pack_format']!=34:raise SystemExit('Invalid pack.')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1 or not installed[0].name.startswith('atlas-core-1.40.'):raise SystemExit('Expected exactly one installed Core 1.40.x; no changes made.')
 url='https://api.atlascobblemon.com.br/minecraft/resourcepacks/'+pack.name
 with urllib.request.urlopen(urllib.request.Request(url,method='HEAD',headers={'User-Agent':'Minecraft Java/1.21.1'}),timeout=20) as response:
  if response.status!=200 or int(response.headers.get('Content-Length','0'))!=pack.stat().st_size:raise SystemExit('Public pack unavailable.')
 print('Verified Atlas Textures, public Minecraft download and 1.21.1 compatibility. Resource pack acceptance will be required.')
 return data,url,installed[0].stem.removeprefix('atlas-core-')

def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required to restart the isolated Minecraft service.')
 data,url,version=preflight();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('required-resource-pack-'+stamp);backup.mkdir(parents=True,mode=0o700)
 properties=SERVER/'server.properties';shutil.copy2(properties,backup/'server.properties');old=properties.read_text()
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  updates={'resource-pack':url.replace(':','\\:'),'resource-pack-sha1':data['sha1'],'resource-pack-id':str(uuid.uuid5(uuid.NAMESPACE_URL,url)),'require-resource-pack':'true','resource-pack-prompt':json.dumps({'text':'O pacote Atlas Textures é obrigatório para jogar no Atlas Cobblemon.','color':'aqua'},ensure_ascii=True)}
  lines=[]
  for line in old.splitlines():
   key=line.split('=',1)[0];lines.append(key+'='+updates.pop(key) if key in updates else line)
  lines.extend(k+'='+v for k,v in updates.items());properties.write_text('\n'.join(lines)+'\n')
  subprocess.run(['systemctl','start','atlas'],check=True)
  deadline=time.monotonic()+100
  while time.monotonic()<deadline:
   active=subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if active and 'Done (' in log and ('atlas-core '+version) in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup health check failed')
  actual=dict(line.split('=',1) for line in properties.read_text().splitlines() if '=' in line and not line.startswith('#'))
  if actual.get('require-resource-pack')!='true' or actual.get('resource-pack','').replace('\\:',':')!=url or actual.get('resource-pack-sha1')!=data['sha1']:raise RuntimeError('Required resource pack setting did not persist')
 except BaseException:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180);shutil.copy2(backup/'server.properties',properties);subprocess.run(['systemctl','start','atlas'],check=True);raise
 print('Atlas Textures is now required. Reconnect and accept the pack to enter. Backup:',backup)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args();apply() if a.apply else preflight()
