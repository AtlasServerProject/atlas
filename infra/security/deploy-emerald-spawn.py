#!/usr/bin/env python3
"""Core 1.40.5: update Emerald arrival to the new lobby, shared by compass and NPC."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric');STAGE=ROOT/'infra/releases/atlas-emerald-spawn-1.40.5'
def properties(raw):
 return {line.split('=',1)[0].strip():line.split('=',1)[1].strip() for line in raw.decode().splitlines() if '=' in line and not line.lstrip().startswith(('#','!'))}
def preflight():
 jar=STAGE/'atlas-core-1.40.5.jar'
 if not jar.exists() or hashlib.sha256(jar.read_bytes()).hexdigest()!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged release missing or checksum mismatch.')
 with zipfile.ZipFile(jar) as z:
  if json.loads(z.read('fabric.mod.json'))['version']!='1.40.5':raise SystemExit('Unexpected release version.')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1 or installed[0].name not in {'atlas-core-1.40.2.jar','atlas-core-1.40.3.jar','atlas-core-1.40.4.jar'}:raise SystemExit('Expected installed Core 1.40.4; no changes made.')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected service user.')
 print('Verified Core 1.40.5. Emerald arrival: 1183.346, 81, 4094.55. Purchases and daily protections preserved.')
 return jar,installed[0]
def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required to restart isolated Minecraft.')
 jar,old=preflight();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('auth-hub-'+stamp);backup.mkdir(parents=True,mode=0o700);shutil.copy2(old,backup/old.name)
 props=(SERVER/'server.properties').read_bytes();owner=old.stat();destination=SERVER/'mods'/jar.name
 rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'atlas-core-1.40.5.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.40.4.jar',s/'atlas-core-1.40.4.jar')
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored. Texture pack and world data untouched.')
''');rollback.write_text(rollback.read_text().replace('atlas-core-1.40.4.jar',old.name));rollback.chmod(0o700)
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  shutil.copy2(jar,destination);os.chown(destination,owner.st_uid,owner.st_gid);destination.chmod(0o644)
  if hashlib.sha256(destination.read_bytes()).hexdigest()!=hashlib.sha256(jar.read_bytes()).hexdigest():raise RuntimeError('Copy checksum mismatch')
  old.unlink()
  if len(list((SERVER/'mods').glob('atlas-core-*.jar')))!=1:raise RuntimeError('Duplicate Core jar')
  subprocess.run(['systemctl','start','atlas'],check=True)
  end=time.monotonic()+100
  while time.monotonic()<end:
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and 'atlas-core 1.40.5' in log and 'Done (' in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup verification failed')
  if properties((SERVER/'server.properties').read_bytes())!=properties(props):raise RuntimeError('Server configuration changed unexpectedly')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Core 1.40.5 active. New Emerald arrival configured for compass and NPC. Rollback:',rollback)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args();apply() if a.apply else preflight()
