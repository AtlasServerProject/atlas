#!/usr/bin/env python3
"""Deploy shop-only Cobblemon machines, with exact-base validation and rollback."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric')
STAGE=ROOT/'infra/releases/atlas-shop-machines-1.40.5-machines.1';VERSION='1.40.5+machines.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
MIGRATION=ROOT/'database/migrations/072_monitor_shop_offer.sql'
def psql(*args,sql=None):
 # SQL goes through stdin: the postgres user cannot read files under /home/somente (mode 0750).
 r=subprocess.run(['sudo','-u','postgres','psql','-X','-v','ON_ERROR_STOP=1','-d','atlas',*args],input=sql,capture_output=True,text=True)
 if r.returncode:raise RuntimeError('psql failed: '+r.stderr.strip())
 return r.stdout.strip()
def migrate():
 if psql('-Atc',f"SELECT count(*) FROM schema_migrations WHERE filename='{MIGRATION.name}'")=='1':return
 psql('--single-transaction',sql=MIGRATION.read_text()+f"\nINSERT INTO schema_migrations(filename) VALUES ('{MIGRATION.name}');\n")
 print('Migration 072 applied: monitor offered in the machines shop.',flush=True)
def preflight():
 jar=STAGE/f'atlas-core-{VERSION}.jar';report=json.loads((STAGE/'verification.json').read_text())
 if sha(jar)!=report['sha256'] or sha(jar)!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged checksum mismatch')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1:raise SystemExit('Expected one Atlas Core')
 old=installed[0]
 if sha(old)==sha(jar):print('Shop-only machines already installed.');return None
 if old.name!='atlas-core-1.40.5+recipe.1.jar' or sha(old)!=report['baseSha256']:raise SystemExit('Installed Core differs from verified base; no changes made')
 with zipfile.ZipFile(old) as a,zipfile.ZipFile(jar) as b:
  added=set()
  if set(b.namelist())!=set(a.namelist())|added or b.testzip() is not None:raise SystemExit('Archive structure mismatch')
  allowed={'fabric.mod.json','io/atlas/mixin/RestrictedRecipeMixin.class','io/atlas/modules/shopkeeper/model/ShopRestrictions.class'}
  changed={n for n in a.namelist() if a.read(n)!=b.read(n)}
  if changed!=allowed:raise SystemExit('Unexpected archive changes')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected service user')
 print('Verified shop-only machines: only the recipe filter and shop restrictions change; worlds, accounts and placed machines preserved.')
 return jar,old

def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required to restart isolated Minecraft service')
 result=preflight()
 if result is None:return
 jar,old=result;stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('shop-machines-'+stamp);backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(old,backup/old.name);owner=old.stat();dest=SERVER/'mods'/jar.name
 rollback=backup/'rollback.py'
 rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'atlas-core-1.40.5+machines.1.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.40.5+recipe.1.jar',s/'atlas-core-1.40.5+recipe.1.jar')
sql="BEGIN; DELETE FROM npc_shop_offers WHERE shop_id='machines' AND item_id='cobblemon:monitor'; DELETE FROM schema_migrations WHERE filename='072_monitor_shop_offer.sql'; COMMIT;"
subprocess.run(['sudo','-u','postgres','psql','-X','-v','ON_ERROR_STOP=1','-d','atlas','-c',sql],check=True)
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored; monitor offer removed.')
''');rollback.chmod(0o700)
 print('Restarting Minecraft gracefully to load shop-only machines.',flush=True)
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  migrate()
  shutil.copy2(jar,dest);os.chown(dest,owner.st_uid,owner.st_gid);dest.chmod(0o644)
  if sha(dest)!=sha(jar):raise RuntimeError('Copy checksum mismatch')
  old.unlink();subprocess.run(['systemctl','start','atlas'],check=True)
  deadline=time.monotonic()+150
  while time.monotonic()<deadline:
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and f'atlas-core {VERSION}' in log and '7 receitas de máquinas Cobblemon removidas' in log and 'Done (' in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup health check failed')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Shop-only machines active. Check that machine recipes no longer craft, planks still do, and the monitor is in the machines shop. Rollback:',rollback)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
 apply() if a.apply else preflight()
