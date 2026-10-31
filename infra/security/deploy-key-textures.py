#!/usr/bin/env python3
"""Install Atlas 1.38.1 + matching key resource pack, preserving service isolation."""
import argparse,datetime,hashlib,json,os,pathlib,pwd,shutil,subprocess,time,urllib.request,uuid,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas')
STAGE=ROOT/'infra/releases/atlas-key-textures-1.38.1'
SERVER=pathlib.Path('/opt/atlas/server/fabric')
PACK='atlas-textures-f2e99dd48aab65f6.zip'
SHA1='f2e99dd48aab65f656b490b418ad42cb8b826018'
PACK_SHA256='7d6e262bcea553ffac2740392472ce374bdc45c13c4e46ac105f7990fc2ef6d3'
URL='https://api.atlascobblemon.com.br/minecraft/resourcepacks/'+PACK

def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def ready(version,timeout=100):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  active=subprocess.run(['systemctl','is-active','--quiet','atlas'],check=False).returncode==0
  log=(SERVER/'logs/latest.log').read_text(errors='replace') if (SERVER/'logs/latest.log').exists() else ''
  if active and 'Done (' in log and (f'atlas-core {version}' in log or f'atlas-core-{version}' in log):return True
  time.sleep(2)
 return False

def preflight():
 jar=STAGE/'atlas-core-1.38.1.jar'
 if not jar.exists() or not jar.with_suffix('.jar.sha256').exists():raise SystemExit('Staged release missing; finish build first.')
 digest=hashlib.sha256(jar.read_bytes()).hexdigest()
 if digest!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged jar checksum mismatch.')
 with zipfile.ZipFile(jar) as z:
  if json.loads(z.read('fabric.mod.json'))['version']!='1.38.1':raise SystemExit('Unexpected jar version.')
 pack=ROOT/'infra/resourcepacks'/PACK
 if hashlib.sha256(pack.read_bytes()).hexdigest()!=PACK_SHA256 or hashlib.sha1(pack.read_bytes()).hexdigest()!=SHA1:raise SystemExit('Resource pack checksum mismatch.')
 with zipfile.ZipFile(pack) as z:
  if z.testzip() or json.loads(z.read('pack.mcmeta'))['pack']['pack_format']!=34:raise SystemExit('Invalid pack.')
  overrides=json.loads(z.read('assets/minecraft/models/item/tripwire_hook.json'))['overrides']
  if len(overrides)!=10:raise SystemExit('Expected ten key models.')
 with urllib.request.urlopen(urllib.request.Request(URL,method='HEAD',headers={'User-Agent':'Minecraft Java/1.21.1'}),timeout=20) as response:
  if response.status!=200 or int(response.headers.get('Content-Length','0'))!=pack.stat().st_size:raise SystemExit('Public resource pack unavailable.')
 service=subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()
 if service!='atlas-minecraft':raise SystemExit('Unexpected service user; refusing to modify isolation.')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1:raise SystemExit('Expected exactly one installed Core jar.')
 if installed[0].name=='atlas-core-1.38.1.jar':raise SystemExit('1.38.1 already installed. No changes needed.')
 if installed[0].name!='atlas-core-1.38.0.jar':raise SystemExit('Unexpected installed Core; review deployment before proceeding.')
 print('Verified 1.38.1, ten website key icons, pack format 34, checksums and public download.')
 print('Apply gracefully restarts Minecraft; preserves worlds, databases and service isolation.')
 return jar,installed[0],digest

def apply():
 if os.geteuid()!=0:raise SystemExit('Root required to stop/start the isolated Minecraft service. Run with sudo.')
 jar,old,digest=preflight()
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('key-textures-'+stamp);backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(old,backup/old.name);shutil.copy2(SERVER/'server.properties',backup/'server.properties')
 account=pwd.getpwnam('atlas-minecraft');destination=SERVER/'mods'/jar.name
 rollback=backup/'rollback.py'
 rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric')
subprocess.run(['systemctl','stop','atlas'],check=True)
(s/'mods/atlas-core-1.38.1.jar').unlink(missing_ok=True)
for jar in p.glob('atlas-core-*.jar'):shutil.copy2(jar,s/'mods'/jar.name)
shutil.copy2(p/'server.properties',s/'server.properties')
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core and pack settings restored; worlds untouched.')
''');rollback.chmod(0o700)
 try:
  # systemctl stop waits for the JVM's normal save/shutdown path.
  run('systemctl','stop','atlas',timeout=180)
  if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0:raise RuntimeError('Service still active')
  shutil.copy2(jar,destination);os.chown(destination,account.pw_uid,old.stat().st_gid);destination.chmod(0o644)
  if hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:raise RuntimeError('Jar copy verification failed')
  old.unlink()
  properties=SERVER/'server.properties';original=properties.read_text()
  updates={'resource-pack':URL.replace(':','\\:'),'resource-pack-sha1':SHA1,'resource-pack-id':str(uuid.uuid5(uuid.NAMESPACE_URL,URL)),'resource-pack-prompt':json.dumps({'text':'Instale Atlas Textures: ícones das chaves, minimapa e GTS.','color':'aqua'},ensure_ascii=True).replace(':','\\:')}
  lines=[]
  for line in original.splitlines():
   key=line.split('=',1)[0]
   if key in updates:lines.append(key+'='+updates.pop(key))
   else:lines.append(line)
  lines.extend(k+'='+v for k,v in updates.items());properties.write_text('\n'.join(lines)+'\n')
  if len(list((SERVER/'mods').glob('atlas-core-*.jar')))!=1:raise RuntimeError('Duplicate Core jar')
  run('systemctl','start','atlas')
  if not ready('1.38.1'):raise RuntimeError('Startup health check failed')
 except BaseException:
  run('/usr/bin/python3',str(rollback));raise
 print('Atlas 1.38.1 active with updated key textures. Reconnect and accept Atlas Textures, then open /compras.')
 print('Backup / rollback:',rollback)
 print('Real-client icon appearance still needs confirmation in Minecraft.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
 apply() if a.apply else preflight()
