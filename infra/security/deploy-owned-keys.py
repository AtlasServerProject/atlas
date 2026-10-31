#!/usr/bin/env python3
"""Core-only 1.38.2 release: hide zero-balance keys. Preserve the installed texture pack."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric');STAGE=ROOT/'infra/releases/atlas-owned-keys-1.38.2'
def preflight():
 jar=STAGE/'atlas-core-1.38.2.jar'
 if not jar.exists() or hashlib.sha256(jar.read_bytes()).hexdigest()!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged release missing or checksum mismatch.')
 with zipfile.ZipFile(jar) as z:
  if json.loads(z.read('fabric.mod.json'))['version']!='1.38.2':raise SystemExit('Unexpected release version.')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1 or installed[0].name!='atlas-core-1.38.1.jar':raise SystemExit('Expected installed Core 1.38.1; no changes made.')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected service user.')
 print('Verified Core 1.38.2. Shows only keys with positive balances. Texture pack preserved.')
 return jar,installed[0]
def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required to restart isolated Minecraft.')
 jar,old=preflight();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('owned-keys-'+stamp);backup.mkdir(parents=True,mode=0o700);shutil.copy2(old,backup/old.name)
 props=(SERVER/'server.properties').read_bytes();owner=old.stat();destination=SERVER/'mods'/jar.name
 rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'atlas-core-1.38.2.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.38.1.jar',s/'atlas-core-1.38.1.jar')
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored. Texture pack and world data untouched.')
''');rollback.chmod(0o700)
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
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and 'atlas-core 1.38.2' in log and 'Done (' in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup verification failed')
  if (SERVER/'server.properties').read_bytes()!=props:raise RuntimeError('Server configuration changed unexpectedly')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Core 1.38.2 active. Open /compras: only owned keys are shown. Rollback:',rollback)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args();apply() if a.apply else preflight()
