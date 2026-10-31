#!/usr/bin/env python3
"""Install local-password login for all valid nicknames; preserve existing identities and data."""
import argparse,datetime,getpass,hashlib,json,os,pathlib,re,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas'); SERVER=pathlib.Path('/opt/atlas/server/fabric')
VERSION='1.40.6'; STAGE=ROOT/'infra/releases/atlas-local-login-1.40.6'
def properties(raw):
 return {line.split('=',1)[0].strip():line.split('=',1)[1].strip() for line in raw.decode().splitlines() if '=' in line and not line.lstrip().startswith(('#','!'))}
def preflight():
 jar=STAGE/f'atlas-core-{VERSION}.jar'
 if not jar.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest()!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged release checksum mismatch.')
 with zipfile.ZipFile(jar) as z:
  if json.loads(z.read('fabric.mod.json'))['version']!=VERSION:raise SystemExit('Unexpected release version.')
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1 or installed[0].name not in {'atlas-core-1.40.2.jar','atlas-core-1.40.3.jar','atlas-core-1.40.4.jar','atlas-core-1.40.5.jar'}:raise SystemExit('Unexpected installed Core; no changes made.')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected service user.')
 print('Verified Core 1.40.6: local /login for all nicknames; existing UUIDs, ranks and passwords preserved.')
 print('Previously passwordless accounts require an initial password in this terminal. No password is printed.')
 return jar,installed[0]
def database():
 config=SERVER/'config/atlas-database.properties'
 values=properties(config.read_bytes()) if config.exists() else {}
 db=values.get('database','atlas');port=values.get('port','5432')
 if not re.fullmatch(r'[A-Za-z0-9_]+',db) or not port.isdigit():raise SystemExit('Unexpected database configuration.')
 return ['runuser','-u','postgres','--','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-p',port,'-d',db]
def sql(command,query):
 return subprocess.run(command,input=query,text=True,capture_output=True,check=True).stdout.strip()
def quote(value):return "'"+str(value).replace("'","''")+"'"
def passwords(command):
 # Refuse to expose a privileged pre-created identity to first-come registration.
 missing=sql(command,"SELECT p.username FROM players p WHERE NOT EXISTS(SELECT 1 FROM auth_accounts a WHERE a.player_id=p.id) AND EXISTS(SELECT 1 FROM player_ranks pr JOIN ranks r ON r.id=pr.rank_id WHERE pr.player_id=p.id AND pr.active AND UPPER(r.identifier) IN ('OWNER','DONO','ADMIN','ADM','MOD','SUP'));")
 if missing:raise SystemExit('Privileged accounts without an authentication record need trusted setup before deployment: '+missing)
 rows=json.loads(sql(command,"SELECT COALESCE(json_agg(t),'[]') FROM (SELECT p.uuid,p.username,a.password_hash FROM players p JOIN auth_accounts a ON a.player_id=p.id WHERE a.password_hash NOT LIKE '$2%') t;"))
 import bcrypt
 for row in rows:
  print('Defina a senha local inicial para a conta existente:',row['username'])
  while True:
   first=getpass.getpass('Nova senha (oculta, mínimo 8 caracteres): ')
   second=getpass.getpass('Confirme a senha (oculta): ')
   if first==second and len(first)>=8 and len(first.encode())<=72:break
   print('As senhas devem ser iguais, ter 8 caracteres ou mais e até 72 bytes.')
  row['new_hash']=bcrypt.hashpw(first.encode(),bcrypt.gensalt(rounds=12,prefix=b'2a')).decode()
 return rows
def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required for isolated Minecraft and account setup.')
 jar,old=preflight();command=database();changes=passwords(command)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=pathlib.Path('/var/backups/atlas-security')/('local-login-'+stamp);backup.mkdir(parents=True,mode=0o700)
 shutil.copy2(old,backup/old.name);credentials=backup/'password-transition.json';credentials.write_text(json.dumps(changes));credentials.chmod(0o600)
 owner=old.stat();destination=SERVER/'mods'/jar.name;props=properties((SERVER/'server.properties').read_bytes())
 rollback=backup/'rollback.py'
 rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,subprocess,shutil,json
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
def q(v):return "'"+str(v).replace("'","''")+"'"
for row in json.loads((p/'password-transition.json').read_text()):
 query='UPDATE auth_accounts a SET password_hash='+q(row['password_hash'])+' FROM players p WHERE a.player_id=p.id AND p.uuid='+q(row['uuid'])+' AND a.password_hash='+q(row['new_hash'])+';'
 subprocess.run(DB_COMMAND,input=query,text=True,capture_output=True,check=True)
(s/NEW_JAR).unlink(missing_ok=True)
shutil.copy2(p/OLD_JAR,s/OLD_JAR)
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored; existing identities and world data preserved.')
'''.replace('DB_COMMAND',repr(command)).replace('NEW_JAR',repr(jar.name)).replace('OLD_JAR',repr(old.name)));rollback.chmod(0o700)
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  if changes:
   query='BEGIN;'+''.join('UPDATE auth_accounts a SET password_hash='+quote(row['new_hash'])+' FROM players p WHERE a.player_id=p.id AND p.uuid='+quote(row['uuid'])+' AND a.password_hash='+quote(row['password_hash'])+' RETURNING p.uuid;' for row in changes)+'COMMIT;'
   updated=sql(command,query).splitlines()
   if set(updated)!={r['uuid'] for r in changes}:raise RuntimeError('Account changed during setup; rollback required.')
  shutil.copy2(jar,destination);os.chown(destination,owner.st_uid,owner.st_gid);destination.chmod(0o644)
  if hashlib.sha256(destination.read_bytes()).hexdigest()!=hashlib.sha256(jar.read_bytes()).hexdigest():raise RuntimeError('Copy checksum mismatch.')
  old.unlink();subprocess.run(['systemctl','start','atlas'],check=True)
  deadline=time.monotonic()+120
  while time.monotonic()<deadline:
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and f'atlas-core {VERSION}' in log and 'Done (' in log:break
   time.sleep(2)
  else:raise RuntimeError('Startup verification failed.')
  if properties((SERVER/'server.properties').read_bytes())!=props:raise RuntimeError('Unexpected server configuration change.')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Local login active. All nicknames require /login or /register. Rollback:',rollback)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');args=p.parse_args();apply() if args.apply else preflight()
