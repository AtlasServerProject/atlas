#!/usr/bin/env python3
"""Register loja/pokecentro/caixas in the isolated server's existing WarpStore."""
import argparse,datetime,json,os,pathlib,shutil,socket,subprocess,time,uuid
SERVER=pathlib.Path('/opt/atlas/server/fabric');FILE=SERVER/'config/atlas/warps.json'
DESTINATIONS=[
 {'name':'loja','title':'Atlas Mart','dimension':'atlas:emerald','x':1236.5,'y':82.0,'z':4064.5,'yaw':-90.0,'pitch':0.0,'icon':'minecraft:gold_ingot'},
 {'name':'pokecentro','title':'Centro Pokémon','dimension':'atlas:emerald','x':1183.5,'y':83.0,'z':4037.5,'yaw':180.0,'pitch':0.0,'icon':'cobblemon:healing_machine'},
 {'name':'caixas','title':'Caixas do Atlas','dimension':'atlas:emerald','x':1243.5,'y':84.0,'z':4029.5,'yaw':180.0,'pitch':0.0,'icon':'minecraft:chest'},
]
def console(command):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(25);s.connect(str(SERVER/'atlas-admin.sock'));s.sendall((command+'\n').encode());s.shutdown(socket.SHUT_WR);return s.makefile().read().strip()
def verify_destinations():
 added=[]
 try:
  for cx,cz in sorted({(int(d['x'])//16,int(d['z'])//16) for d in DESTINATIONS}):
   result=console(f'execute in atlas:emerald run forceload query {cx*16} {cz*16}')
   if 'not marked' in result.lower():console(f'execute in atlas:emerald run forceload add {cx*16} {cz*16}');added.append((cx,cz))
   elif 'marked' not in result.lower():raise RuntimeError('Could not verify temporary chunk loading')
  time.sleep(1)
  for d in DESTINATIONS:
   x,y,z=int(d['x']),int(d['y']),int(d['z'])
   for dy in [0,1]:
    result=console(f'execute in atlas:emerald if block {x} {y+dy} {z} minecraft:air')
    if 'passed' not in result.lower():raise RuntimeError('Destination obstructed: '+d['name'])
   expected={'loja':'minecraft:polished_deepslate','pokecentro':'minecraft:smooth_quartz','caixas':'minecraft:dark_oak_planks'}[d['name']]
   result=console(f'execute in atlas:emerald if block {x} {y-1} {z} {expected}')
   if 'passed' not in result.lower():raise RuntimeError('Destination floor changed: '+d['name'])
 finally:
  for cx,cz in added:console(f'execute in atlas:emerald run forceload remove {cx*16} {cz*16}')
def preflight():
 installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
 if len(installed)!=1 or installed[0].name not in {'atlas-core-1.40.5+warp.1.jar','atlas-core-1.40.5+lobby.1.jar'}:raise SystemExit('Expected the installed Atlas warps release; no changes made.')
 if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected Minecraft service user')
 verify_destinations()
 print('Verified three safe destinations in the current lobby:')
 for d in DESTINATIONS:print(f"/warp {d['name']}: {d['x']}, {d['y']}, {d['z']}; yaw {d['yaw']}")
def apply():
 if os.geteuid()!=0:raise SystemExit('sudo required: warp config belongs to isolated Minecraft user.')
 preflight();document=json.loads(FILE.read_text())
 if document.get('schemaVersion')!=1 or not isinstance(document.get('warps'),list):raise SystemExit('Invalid current warp catalogue; unchanged.')
 names=[d['name'] for d in document['warps']]
 if len(names)!=len(set(names)):raise SystemExit('Duplicate current warp names; unchanged.')
 # Preserve every unrelated destination. These three requested destinations are public.
 entries={d['name']:d for d in document['warps']}
 for destination in DESTINATIONS:entries[destination['name']]={**destination,'access':'PUBLIC','enabled':True,'revision':str(uuid.uuid4())}
 document['warps']=[entries[name] for name in sorted(entries)]
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=pathlib.Path('/var/backups/atlas-security')/('lobby-warps-'+stamp)
 backup.mkdir(parents=True,mode=0o700);shutil.copy2(FILE,backup/'warps.json');owner=FILE.stat()
 if FILE.with_suffix('.json.bak').exists():shutil.copy2(FILE.with_suffix('.json.bak'),backup/'warps.json.bak')
 rollback=backup/'rollback.py'
 rollback.write_text(f'''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;dest=pathlib.Path({str(FILE)!r})
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
shutil.copy2(p/'warps.json',dest);os.chown(dest,{owner.st_uid},{owner.st_gid})
if (p/'warps.json.bak').exists():shutil.copy2(p/'warps.json.bak',dest.with_suffix('.json.bak'));os.chown(dest.with_suffix('.json.bak'),{owner.st_uid},{owner.st_gid})
else:dest.with_suffix('.json.bak').unlink(missing_ok=True)
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous warp catalogue restored. World lighting unchanged.')
''');rollback.chmod(0o700)
 print('Restarting Minecraft to load the three warps. Existing destinations and lighting are preserved.',flush=True)
 try:
  subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
  temp=FILE.with_name('warps.setup.tmp')
  with temp.open('w') as f:json.dump(document,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.chown(temp,owner.st_uid,owner.st_gid);temp.chmod(0o600)
  shutil.copy2(FILE,FILE.with_suffix('.json.bak'));os.chown(FILE.with_suffix('.json.bak'),owner.st_uid,owner.st_gid)
  temp.replace(FILE)
  subprocess.run(['systemctl','start','atlas'],check=True)
  until=time.monotonic()+150
  while time.monotonic()<until:
   log=(SERVER/'logs/latest.log').read_text(errors='replace')
   if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and 'Done (' in log and f'Warps Atlas: {len(entries)} destinos carregados.' in log:break
   time.sleep(2)
  else:raise RuntimeError('Minecraft/warps startup health check failed')
 except BaseException:
  subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
 print('Active: /warp loja, /warp pokecentro, /warp caixas. Rollback:',rollback)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true')
 apply() if parser.parse_args().apply else preflight()
