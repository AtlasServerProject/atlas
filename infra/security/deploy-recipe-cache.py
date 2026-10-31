#!/usr/bin/env python3
"""Deploy only the tag-based crafting fix, with exact-base validation and rollback."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric')
STAGE=ROOT/'infra/releases/atlas-recipe-cache-1.40.5-recipe.1';VERSION='1.40.5+recipe.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def preflight():
 jar=STAGE/f'atlas-core-{VERSION}.jar';report=json.loads((STAGE/'verification.json').read_text())
 if sha(jar)!=report['sha256'] or sha(jar)!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged checksum mismatch')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1:raise SystemExit('Expected one Atlas Core')
 old=installed[0]
 if sha(old)==sha(jar):print('Crafting fix already installed.');return None
 if old.name!='atlas-core-1.40.5+lobby.2.jar' or sha(old)!=report['baseSha256']:raise SystemExit('Installed Core differs from verified base; no changes made')
 with zipfile.ZipFile(old) as a,zipfile.ZipFile(jar) as b:
  added={'io/atlas/mixin/IngredientCacheAccessor.class'}
  if set(b.namelist())!=set(a.namelist())|added or b.testzip() is not None:raise SystemExit('Archive structure mismatch')
  allowed={'fabric.mod.json','atlas-core.mixins.json','io/atlas/mixin/RestrictedRecipeMixin.class'}
  changed={n for n in a.namelist() if a.read(n)!=b.read(n)}
  if changed!=allowed:raise SystemExit('Unexpected archive changes')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected service user')
 print('Verified crafting fix: only the recipe filter and its cache accessor change; worlds, accounts and rewards preserved.')
 return jar,old

def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required to restart isolated Minecraft service')
 result=preflight()
 if result is None:return
 jar,old=result;stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('recipe-cache-'+stamp);backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(old,backup/old.name);owner=old.stat();dest=SERVER/'mods'/jar.name
 rollback=backup/'rollback.py'
 rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'atlas-core-1.40.5+recipe.1.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.40.5+lobby.2.jar',s/'atlas-core-1.40.5+lobby.2.jar')
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored.')
''');rollback.chmod(0o700)
 print('Restarting Minecraft gracefully to load the crafting fix.',flush=True)
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  shutil.copy2(jar,dest);os.chown(dest,owner.st_uid,owner.st_gid);dest.chmod(0o644)
  if sha(dest)!=sha(jar):raise RuntimeError('Copy checksum mismatch')
  old.unlink();subprocess.run(['systemctl','start','atlas'],check=True)
  deadline=time.monotonic()+150
  while time.monotonic()<deadline:
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and f'atlas-core {VERSION}' in log and 'receitas com Bottle Caps removidas' in log and 'Done (' in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup health check failed')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Crafting fix active. Test oak planks, sticks and a crafting table in Survival. Rollback:',rollback)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
 apply() if a.apply else preflight()
