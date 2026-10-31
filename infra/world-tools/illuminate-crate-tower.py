#!/usr/bin/env python3
"""Place verified hanging lanterns via the Minecraft console; preserve per-block rollback."""
import argparse,importlib.util,json,pathlib,socket,time
ROOT=pathlib.Path('/home/somente/dev/atlas')
BACKUP=pathlib.Path(pathlib.Path('/tmp/atlas-tower-backup-path').read_text())
spec=importlib.util.spec_from_file_location('region',ROOT/'infra/world-tools/inspect-region.py');region=importlib.util.module_from_spec(spec);spec.loader.exec_module(region)
def console(command):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(25);s.connect('/opt/atlas/server/fabric/atlas-admin.sock');s.sendall((command+'\n').encode());s.shutdown(socket.SHUT_WR);return s.makefile().read().strip()
def state(value):
 props=value.get('Properties',{})
 return value['Name']+('['+','.join(k+'='+v for k,v in sorted(props.items()))+']' if props else '')
def make_plan():
 r=region.Region(BACKUP/'region/r.2.7.mca');edits=[];lamps=[]
 for floor,roof,offset in [(83,89,6),(90,95,5),(96,101,4),(102,107,3),(108,112,2),(113,117,2),(118,122,2)]:
  y=roof-(2 if roof-floor>=5 else 1)
  for dx,dz in [(-offset,-offset),(offset,-offset),(-offset,offset),(offset,offset),(0,0)]:
   x,z=1243+dx,4022+dz
   # Sixth floor's staircase occupies the south corners: shift both lamps toward the wall symmetrically.
   if floor==113 and dz>0:z=4026
   support=r.block(x,roof,z)
   if support['Name']!='minecraft:deepslate_tiles':raise RuntimeError('Lamp lacks full ceiling support: '+str((x,roof,z)))
   for h in range(y,roof):
    old=r.block(x,h,z)
    if old['Name']!='minecraft:air':raise RuntimeError('Refusing to replace an existing block: '+str((x,h,z,old)))
   # Supports first; then the lamp. Keep regular lanterns (light 15), not dim soul lanterns.
   for h in range(roof-1,y,-1):edits.append({'pos':[x,h,z],'before':r.block(x,h,z),'after':{'Name':'minecraft:chain','Properties':{'axis':'y','waterlogged':'false'}}})
   edits.append({'pos':[x,y,z],'before':r.block(x,y,z),'after':{'Name':'minecraft:lantern','Properties':{'hanging':'true','waterlogged':'false'}}})
   lamps.append([x,y,z])
 result={'dimension':'atlas:emerald','backup':str(BACKUP),'lamps':lamps,'edits':edits,'applied':[]}
 return result

def apply(plan):
 log=BACKUP/'lighting-changes.json';log.write_text(json.dumps(plan,indent=2)+'\n')
 chunks=sorted({(e['pos'][0]//16,e['pos'][2]//16) for e in plan['edits']});added=[]
 try:
  for cx,cz in chunks:
   query=console(f'execute in atlas:emerald run forceload query {cx*16} {cz*16}')
   if 'not marked' in query.lower() or 'not force loaded' in query.lower():
    reply=console(f'execute in atlas:emerald run forceload add {cx*16} {cz*16}');added.append((cx,cz))
   elif 'marked' not in query.lower() and 'force loaded' not in query.lower():raise RuntimeError('Unexpected forceload response: '+query)
  time.sleep(1)
  # Check ALL intended edits before changing anything, catching live changes after the snapshot.
  for e in plan['edits']:
   xyz=' '.join(map(str,e['pos']));reply=console(f'execute in atlas:emerald if block {xyz} {state(e["before"])}')
   if 'passed' not in reply.lower():raise RuntimeError('Preflight block changed: '+xyz+' '+reply)
  for e in plan['edits']:
   xyz=' '.join(map(str,e['pos']));reply=console(f'execute in atlas:emerald if block {xyz} {state(e["before"])} run setblock {xyz} {state(e["after"])}')
   if 'changed' not in reply.lower():raise RuntimeError('Placement failed: '+xyz+' '+reply)
   plan['applied'].append(e);log.write_text(json.dumps(plan,indent=2)+'\n')
  for e in plan['edits']:
   xyz=' '.join(map(str,e['pos']));reply=console(f'execute in atlas:emerald if block {xyz} {state(e["after"])}')
   if 'passed' not in reply.lower():raise RuntimeError('Verification failed: '+xyz+' '+reply)
  console('save-all flush');print(f'Placed and verified {len(plan["lamps"])} lanterns; {len(plan["edits"])} block edits. Backup/rollback journal: {log}')
 except BaseException:
  for e in reversed(plan['applied']):
   xyz=' '.join(map(str,e['pos']));console(f'execute in atlas:emerald if block {xyz} {state(e["after"])} run setblock {xyz} {state(e["before"])}')
  console('save-all flush');raise
 finally:
  for cx,cz in added:console(f'execute in atlas:emerald run forceload remove {cx*16} {cz*16}')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();plan=make_plan()
 print('Plan:',len(plan['lamps']),'hanging lanterns across seven floors;',len(plan['edits']),'air-only changes.')
 if args.apply:apply(plan)
