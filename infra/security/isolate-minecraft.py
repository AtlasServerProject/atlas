#!/usr/bin/env python3
"""Run with sudo --apply after reviewing. Changes OS ownership/sandbox only, no world blocks.
Rollback instructions and original unit are saved root-only in /var/backups/atlas-security/.
"""
import argparse,datetime,grp,json,os,pathlib,pwd,shutil,socket,stat,subprocess,sys,time
BASE=pathlib.Path('/opt/atlas/server/fabric')
DROP=pathlib.Path('/etc/systemd/system/atlas.service.d/70-security-isolation.conf')
USER='atlas-minecraft';GROUP='atlas-operators';OPERATOR='somente'
def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def inspect():
 expected=pwd.getpwnam(OPERATOR).pw_uid
 if BASE.is_symlink() or not (BASE/'world/level.dat').is_file():raise SystemExit('Unexpected server layout; refusing.')
 if DROP.exists():raise SystemExit('Isolation drop-in already exists; inspect status instead of rerunning.')
 for current,dirs,files in os.walk(BASE,followlinks=False):
  for name in dirs+files:
   p=pathlib.Path(current)/name;st=p.lstat()
   if stat.S_ISLNK(st.st_mode):raise SystemExit('Symlink in server tree: review manually before isolation.')
   if st.st_uid!=expected and not (st.st_uid==0 and p==BASE/'config/chunky/config.json'):raise SystemExit('Unexpected file owner in server tree: review manually.')
 print('Preflight: dedicated user + group, ownership change, private home, read-only OS, controlled write directory.')
 print('A graceful Minecraft restart is required. No world data is deleted or edited.')
def apply():
 if os.geteuid()!=0:raise SystemExit('Linux root required: sudo python3 '+__file__+' --apply')
 inspect()
 backup=pathlib.Path('/var/backups/atlas-security')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup.mkdir(parents=True,mode=0o700)
 (backup/'atlas-original.unit').write_bytes(subprocess.check_output(['systemctl','cat','atlas.service']))
 try:grp.getgrnam(GROUP)
 except KeyError:run('groupadd','--system',GROUP)
 try:pwd.getpwnam(USER)
 except KeyError:run('useradd','--system','--no-create-home','--home-dir','/var/lib/atlas-minecraft','--shell','/usr/sbin/nologin','--gid',GROUP,USER)
 run('usermod','--append','--groups',GROUP,OPERATOR)
 old=pwd.getpwnam(OPERATOR);new=pwd.getpwnam(USER);group=grp.getgrnam(GROUP).gr_gid
 run('systemctl','stop','atlas.service')
 if subprocess.run(['systemctl','is-active','--quiet','atlas.service']).returncode==0:raise SystemExit('Minecraft still running; no ownership changes made.')
 # Record exact original ownership and permissions for reversible metadata-only changes.
 records=[]
 for current,dirs,files in os.walk(BASE,followlinks=False):
  for p in [pathlib.Path(current)]+[pathlib.Path(current)/n for n in files]:
   st=p.lstat();records.append([str(p),st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode)])
 (backup/'metadata.json').write_text(json.dumps(records));(backup/'metadata.json').chmod(0o600)
 helper=pathlib.Path('/usr/local/libexec/atlas-admin-socket-access.py');helper.parent.mkdir(parents=True,exist_ok=True)
 helper.write_text('''#!/usr/bin/python3
import os,pathlib,stat,time
p=pathlib.Path('/opt/atlas/server/fabric/atlas-admin.sock')
for i in range(120):
 try:
  if stat.S_ISSOCK(p.lstat().st_mode):os.chmod(p,0o660);break
 except FileNotFoundError:pass
 time.sleep(1)
else:raise SystemExit('Admin socket did not become available')
''');helper.chmod(0o755)
 DROP.parent.mkdir(parents=True,exist_ok=True)
 DROP.write_text('''[Service]
User=atlas-minecraft
Group=atlas-operators
UMask=0007
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/opt/atlas/server/fabric
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
LimitCORE=0
ExecStartPost=/usr/bin/python3 /usr/local/libexec/atlas-admin-socket-access.py
''')
 for name,uid,gid,mode in records:
  os.chown(name,new.pw_uid,group,follow_symlinks=False)
  # Operator retains existing administrative editing access via a restricted group.
  os.chmod(name,mode | (stat.S_IRGRP if mode&stat.S_IRUSR else 0) | (stat.S_IWGRP if mode&stat.S_IWUSR else 0) | (stat.S_IXGRP if mode&stat.S_IXUSR else 0))
 rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/python3
import json,os,pathlib,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
subprocess.run(['systemctl','stop','atlas.service'],check=True)
for name,uid,gid,mode in json.loads(pathlib.Path(__file__).with_name('metadata.json').read_text()):
 if pathlib.Path(name).exists():os.chown(name,uid,gid);os.chmod(name,mode)
pathlib.Path('/etc/systemd/system/atlas.service.d/70-security-isolation.conf').unlink(missing_ok=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','atlas.service'],check=True)
''');rollback.chmod(0o700)
 run('systemctl','daemon-reload')
 try:
  run('systemctl','start','atlas.service')
  run('systemctl','is-active','--quiet','atlas.service')
  # Prove the game UID cannot read credentials belonging to the API operator.
  target=pathlib.Path('/home/somente/dev/atlas/atlas-api/.env')
  if subprocess.run(['runuser','-u',USER,'--','test','-r',str(target)]).returncode==0:raise RuntimeError('Isolation verification failed')
 except Exception:
  print('Verification failed. Restoring original metadata and unit.',file=sys.stderr);run('python3',str(rollback));raise
 print('Isolation active. Rollback:',rollback)
 print('Reconnect VS Code/terminal to pick up atlas-operators group membership.')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if args.apply:apply()
 else:inspect()
