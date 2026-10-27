#!/usr/bin/env python3
"""Archive only atlas:emerald while Minecraft is stopped; recreate its empty void storage."""
import argparse,datetime,hashlib,json,os,pathlib,pwd,shutil,socket,subprocess,time
SERVER=pathlib.Path('/opt/atlas/server/fabric');WORLD=SERVER/'world';SOURCE=WORLD/'dimensions/atlas/emerald'
VERIFIED=pathlib.Path('/home/somente/backups/lobby-emerald/current-20261025T184405Z')
def preflight():
 if not (VERIFIED/'VERIFIED.txt').is_file():raise SystemExit('Previous verified backup missing; refusing.')
 if SOURCE.is_symlink() or SOURCE.resolve()!=WORLD.resolve()/'dimensions/atlas/emerald':raise SystemExit('Unexpected dimension path')
 definition=json.loads((WORLD/'datapacks/atlas-lobbies/data/atlas/dimension/emerald.json').read_text());settings=definition.get('generator',{}).get('settings',{})
 if definition.get('generator',{}).get('type')!='minecraft:flat' or settings.get('layers')!=[]:raise SystemExit('Emerald generator is not empty void; review before clearing.')
 manifest=json.loads((VERIFIED/'manifest.json').read_text())
 for relative,entry in manifest['files'].items():
  path=VERIFIED/'emerald'/relative
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise SystemExit('Previous backup failed integrity verification')
 print('Verified previous backup and empty-void generator. Scope: atlas:emerald only.',flush=True)
def command(text):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(90);s.connect(str(SERVER/'atlas-admin.sock'));s.sendall((text+'\n').encode());s.shutdown(socket.SHUT_WR);parts=[]
  while True:
   b=s.recv(65536)
   if not b:break
   parts.append(b)
  return b''.join(parts).decode(errors='replace')
def apply():
 if os.geteuid()!=0:raise SystemExit('Run with sudo and --apply: stopping the isolated system service requires root.')
 preflight();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=pathlib.Path('/home/somente/backups/lobby-emerald')/('before-clear-'+stamp);backup.mkdir(mode=0o700)
 # Move current online players to Auth Lobby so no player remains in the removed dimension.
 command('execute in atlas:emerald as @a[distance=0..] in minecraft:overworld run tp @s 642 126 3534')
 saved=command('save-all flush')
 if 'Saved the game' not in saved:raise SystemExit('World save was not confirmed; refusing.')
 subprocess.run(['systemctl','stop','atlas.service'],check=True)
 if subprocess.run(['systemctl','is-active','--quiet','atlas.service']).returncode==0:raise SystemExit('Server still running; no files moved.')
 try:
  entries={}
  for p in SOURCE.rglob('*'):
   if p.is_symlink():raise RuntimeError('Unexpected symlink in dimension')
   if p.is_file():entries[str(p.relative_to(SOURCE))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
  if not entries:raise RuntimeError('Dimension already empty; review instead of overwriting')
  (backup/'manifest.json').write_text(json.dumps({'dimension':'atlas:emerald','createdUtc':stamp,'files':entries},indent=2))
  SOURCE.rename(backup/'emerald')
  user=pwd.getpwnam('atlas-minecraft');SOURCE.mkdir(mode=0o775);os.chown(SOURCE,user.pw_uid,user.pw_gid)
  for name,entry in entries.items():
   if hashlib.sha256((backup/'emerald'/name).read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Archive integrity mismatch')
  (backup/'VERIFIED.txt').write_text('Current dimension archived with SHA256 manifest; source recreated empty. Other dimensions/playerdata untouched.\n')
  operator=pwd.getpwnam('somente');os.chown(backup,operator.pw_uid,operator.pw_gid)
  for filename in ('manifest.json','VERIFIED.txt'):os.chown(backup/filename,operator.pw_uid,operator.pw_gid)
 except Exception:
  if (backup/'emerald').exists():
   if SOURCE.exists() and not list(SOURCE.iterdir()):SOURCE.rmdir()
   if not SOURCE.exists():(backup/'emerald').rename(SOURCE)
  subprocess.run(['systemctl','start','atlas.service'],check=True);raise
 subprocess.run(['systemctl','start','atlas.service'],check=True)
 print('Emerald cleared to empty void. Current snapshot:',backup,flush=True)
 print('Original verified backup preserved:',VERIFIED,flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if args.apply:apply()
 else:preflight()
