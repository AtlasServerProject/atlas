#!/usr/bin/env python3
"""Furnish the existing Emerald castle through guarded vanilla console commands.

Reads an immutable pre-decoration snapshot. Every changed block is journaled;
rollback checks the new state before restoring the old one. Never edits Anvil files.
"""
import argparse, collections, importlib.util, json, pathlib, socket, time
ROOT=pathlib.Path('/home/somente/dev/atlas')
BACKUP=pathlib.Path('/home/somente/backups/lobby-emerald/professors-hall-20261030T180027Z')
TAG='atlas_professors_castle'
spec=importlib.util.spec_from_file_location('region',ROOT/'infra/world-tools/inspect-region.py')
region=importlib.util.module_from_spec(spec);spec.loader.exec_module(region)
def console(command):
 if len(command)>2048:raise ValueError('Console command too long')
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(30);s.connect('/opt/atlas/server/fabric/atlas-admin.sock')
  s.sendall((command+'\n').encode());s.shutdown(socket.SHUT_WR)
  return s.makefile().read().strip()
def state(b):
 p=b.get('Properties',{})
 return b['Name']+('['+','.join(k+'='+v for k,v in sorted(p.items()))+']' if p else '')
def block(name,**props):return {'Name':'minecraft:'+name,**({'Properties':{k:str(v).lower() for k,v in props.items()}} if props else {})}
AIR=block('air')
def make_plan():
 r=region.Region(BACKUP/'region/r.2.7.mca');planned={};labels=[];lamps=[];routes=[]
 def get(x,y,z):return planned.get((x,y,z),r.block(x,y,z))
 def put(x,y,z,name,replace=False,**props):
  assert 1114<=x<=1136 and 4047<=z<=4077 and 81<=y<=103,(x,y,z)
  before=get(x,y,z)
  if not replace and before['Name']!='minecraft:air':raise ValueError(('Occupied',x,y,z,before,name))
  if before['Name'].endswith('glass_pane'):raise ValueError('Window protected')
  planned[x,y,z]=block(name,**props)
 def line(x1,x2,y,z,name,**props):
  for x in range(x1,x2+1):put(x,y,z,name,**props)
 def title(text,x,y,z,scale=.55):labels.append({'text':text,'pos':[x,y,z],'scale':scale})
 def light(x,y,z,roof):
  assert get(x,roof,z)['Name']!='minecraft:air',('No roof',x,roof,z)
  for h in range(roof-1,y,-1):put(x,h,z,'chain',axis='y',waterlogged=False)
  put(x,y,z,'lantern',hanging=True,waterlogged=False);lamps.append([x,y,z])
 def bookshelf(x,y,z,height=2):
  for h in range(height):put(x,y+h,z,'bookshelf')
  put(x,y+height,z,'dark_oak_slab',type='bottom',waterlogged=False)
 def desk(x,y,z,facing='east'):
  put(x,y,z,'dark_oak_planks');put(x,y+1,z,'lectern',facing=facing,has_book=False,powered=False)
 # Ground floor: stone-to-quartz inlay contained strictly within the existing floor.
 for x in range(1118,1133):
  for z in range(4051,4074):
   if r.block(x,81,z)['Name']=='minecraft:stone_bricks':
    put(x,81,z,'polished_andesite' if x in [1118,1132] or z in [4051,4073] else 'smooth_quartz',replace=True)
 # Central ceremony stage (west), blue runner from east entrance.
 for x in range(1118,1121):
  for z in range(4059,4066):put(x,82,z,'smooth_quartz')
 for z in range(4060,4065):put(1121,82,z,'quartz_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
 for x in range(1122,1133):
  for z in range(4061,4064):put(x,82,z,'blue_carpet')
 for z in [4060,4064]:
  for x in range(1122,1133):put(x,81,z,'polished_blackstone',replace=True)
 for z in [4061,4063]:
  for y in range(83,86):put(1118,y,z,'quartz_pillar',axis='y')
  put(1118,86,z,'gold_block')
 put(1118,84,4062,'chiseled_quartz_block');put(1118,85,4062,'amethyst_block')
 for x in [1124,1127]:
  for z in list(range(4057,4060))+list(range(4065,4068)):
   put(x,82,z,'dark_oak_stairs',facing='east',half='bottom',shape='straight',waterlogged=False)
 # Reception desk against east wall, clear of central door and north tower passage.
 for z in range(4055,4059):put(1131,82,z,'dark_oak_planks')
 put(1131,83,4055,'potted_fern');put(1131,83,4057,'lectern',facing='west',has_book=False,powered=False)
 for x in [1123,1127]:
  bookshelf(x,82,4051,2);bookshelf(x,82,4073,2)
 for x in [1124,1126]:
  put(x,82,4051,'dark_oak_planks');put(x,83,4051,'potted_azalea_bush')
  put(x,82,4073,'dark_oak_planks');put(x,83,4073,'potted_flowering_azalea_bush')
 for z in [4055,4069]:
  put(1131,82,z,'chiseled_quartz_block',replace=(z==4055))
 # Staircases: two blocks wide, guarded open headroom to both upper floors.
 for base,n,start in [(82,6,4070),(88,5,4063)]:
  ceiling=87 if base==82 else 92
  for x in [1119,1120]:
   for i in range(n):
    z=start-i;y=base+i
    for h in range(base,y):
     if get(x,h,z)['Name']=='minecraft:air':put(x,h,z,'dark_oak_planks')
    for h in [y+1,y+2]:
     if h==ceiling:put(x,h,z,'air',replace=True)
    put(x,y,z,'dark_oak_stairs',replace=(y==ceiling),facing='north',half='bottom',shape='straight',waterlogged=False)
    routes.append([x,y+.5,z])
   for z in range(start-n+2,start+1):
    # Rail sits beside the stair, not across the climb or landing.
    h=min(base+start-z+1,ceiling+1)
    if get(1121,h,z)['Name']=='minecraft:air':put(1121,h,z,'dark_oak_fence',waterlogged=False)
 # Extra guard for edges of each floor opening.
 for y,zs in [(88,[4065,4066,4067]),(93,[4059,4060,4061])]:
  for z in zs:
   for x in [1118,1121]:
    if get(x,y,z)['Name']=='minecraft:air':put(x,y,z,'dark_oak_fence',waterlogged=False)
 # Second floor: a spacious gallery with reserved plinths and research benches.
 for x in range(1123,1131):
  for z in range(4061,4064):put(x,88,z,'cyan_carpet')
 for z in [4055,4058,4066,4069]:
  put(1131,88,z,'chiseled_quartz_block');put(1131,89,z,'amethyst_cluster',facing='up',waterlogged=False)
 for x in [1123,1127]:
  for z in [4052,4072]:
   bookshelf(x,88,z,2)
   put(x+1,88,z,'dark_oak_planks');put(x+1,89,z,'potted_fern')
 for z in [4055,4057,4068,4070]:
  put(1124,88,z,'dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
  put(1123,88,z,'spruce_slab',type='top',waterlogged=False)
 # Attic: archive shelves, a conference table and quiet reading alcoves.
 for x in [1122,1124,1126,1128]:
  bookshelf(x,93,4052,3);bookshelf(x,93,4072,3)
 for z in range(4055,4070):
  if z in [4059,4060,4061,4062,4063,4064]:continue
  bookshelf(1131,93,z,2)
 for x in range(1124,1128):
  for z in range(4060,4065):put(x,93,z,'dark_oak_slab',type='top',waterlogged=False)
 for z in [4060,4062,4064]:
  put(1123,93,z,'dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
  put(1128,93,z,'dark_oak_stairs',facing='east',half='bottom',shape='straight',waterlogged=False)
 put(1125,94,4062,'potted_flowering_azalea_bush')
 put(1131,93,4062,'lectern',facing='west',has_book=False,powered=False)
 for z in [4055,4069]:
  put(1121,93,z,'dark_oak_planks');put(1121,94,z,'potted_fern')
 # Four towers, all three levels: internal doors, ladder shaft, individual study nooks.
 for cx,cz,dx,dz,name in [(1117,4050,1,1,'Pesquisa'),(1133,4050,-1,1,'Descobertas'),(1117,4074,1,-1,'Memórias'),(1133,4074,-1,-1,'Conhecimento')]:
  for floor in [82,88]:
   for x in [cx+2*dx,cx+dx]:
    for h in range(floor+1,floor+4):put(x,h,cz+2*dz,'air',replace=True)
   put(cx+3*dx,floor,cz+2*dz,'dark_oak_stairs',facing='west' if dx==1 else 'east',half='bottom',shape='straight',waterlogged=False)
  # Ladder uses an existing full north-wall support on every level.
  for y in range(83,97):
   assert r.block(cx,y,cz-3)['Name']!='minecraft:air'
   put(cx,y,cz-2,'ladder',replace=True,facing='south',waterlogged=False)
  for floor in [82,88,94]:
   y=floor+1
   bx,bz=cx-dx,cz-dz
   bookshelf(bx,y,bz,2)
   put(cx-dx,y,cz+dz,'lectern',facing='east' if dx==1 else 'west',has_book=False,powered=False)
   put(cx-2*dx,y,cz,'dark_oak_stairs',facing='west' if dx==1 else 'east',half='bottom',shape='straight',waterlogged=False)
   # Central lantern hangs high enough to keep a two-block walking clearance.
   light(cx,floor+4 if floor<94 else 101,cz,88 if floor==82 else 94 if floor==88 else 104)
  title(name,cx,85.7,cz,.3)
 # Warm lighting: three rows per main floor, central vault chandeliers.
 for x in [1120,1125,1130]:
  for z in [4055,4062,4069]:
   # Avoid stage decoration and stair structure.
   if x==1120 and z==4062:continue
   if x==1120 and z==4069:continue
   light(x,85,z,87)
   light(x,90,z,92)
 for z in [4055,4062,4069]:
  light(1125,98,z,102)
 for x in [1120,1130]:
  for z in [4055,4062,4069]:light(x,96,z,97)
 title('HALL DOS PROFESSORES',1134.1,85.0,4062.5,.65)
 title('Legado de quem completou a Pokédex',1119.0,86,4062.5,.38)
 title('Galeria de conquistas',1127,90.5,4062,.45)
 title('Biblioteca e arquivo Atlas',1125,97,4067,.45)
 title('Consulte as homenagens com o curador',1129,84.7,4056.5,.26)
 # Route clearance checks for each individual stair (at its highest half).
 for x,half,z in routes:
  y=int(half)
  for h in [y+1,y+2]:
   if get(x,h,z)['Name']!='minecraft:air':raise ValueError(('Stair headroom',x,h,z,get(x,h,z)))
 # Every external window and all roof/wall decoration stays untouched, except explicitly listed internal tower doors.
 edits=[]
 for pos,after in planned.items():
  before=r.block(*pos)
  if state(before)!=state(after):edits.append({'pos':list(pos),'before':before,'after':after})
 return {'dimension':'atlas:emerald','backup':str(BACKUP),'tag':TAG,'edits':edits,'labels':labels,'lamps':lamps,'applied':[]}

def batches(edits):
 # Maintain support-before-decoration ordering. Combine adjacent X cells only.
 groups=[]
 for e in edits:
  if groups:
   g=groups[-1];last=g[-1]
   if len(g)<5 and e['pos'][1:]==last['pos'][1:] and e['pos'][0]==last['pos'][0]+1 and state(e['after'])==state(last['after']):
    g.append(e);continue
  groups.append([e])
 return groups

def guarded(group,reverse=False):
 before='after' if reverse else 'before';after='before' if reverse else 'after'
 # Reverse batches may have different originals; restore separately then.
 if reverse and len({state(e[after]) for e in group})>1:
  return [guarded([e],True)[0] for e in group]
 checks=' '.join('if block '+' '.join(map(str,e['pos']))+' '+state(e[before]) for e in group)
 a=' '.join(map(str,group[0]['pos']));b=' '.join(map(str,group[-1]['pos']))
 action=f'setblock {a} {state(group[0][after])}' if len(group)==1 else f'fill {a} {b} {state(group[0][after])}'
 return [f'execute in atlas:emerald {checks} run {action}']

def create_entities(plan):
 for i,label in enumerate(plan['labels']):
  xyz=' '.join(map(str,label['pos']));scale=label['scale']
  component=json.dumps({'text':label['text'],'color':'#72E5FA','bold':True},ensure_ascii=False)
  nbt='{Tags:["'+TAG+'","'+TAG+'_label_'+str(i)+'"],text:'+json.dumps(component,ensure_ascii=False)+',billboard:"center",alignment:"center",background:0,shadow:1b,see_through:0b,line_width:360,view_range:1.2f,brightness:{block:15,sky:15},transformation:{translation:[0f,0f,0f],left_rotation:[0f,0f,0f,1f],scale:['+','.join([str(scale)+'f']*3)+'],right_rotation:[0f,0f,0f,1f]}}'
  reply=console('execute in atlas:emerald run summon minecraft:text_display '+xyz+' '+nbt)
  if 'summoned' not in reply.lower():raise RuntimeError(reply)
 template=(ROOT/'infra/templates/npcs/emerald-professor-carvalho.mcfunction').read_text().splitlines()[-1]
 nbt=template[template.index('{Tags:'):]
 nbt=nbt.replace('"atlas_npc_emerald_professor_carvalho"','"'+TAG+'","atlas_npc_hall_professores"')
 nbt=nbt.replace('Professor Carvalho','Curador do Hall').replace('"green"','"gold"').replace('Rotation:[180f,0f]','Rotation:[-90f,0f]')
 reply=console('execute in atlas:emerald run summon easy_npc:humanoid 1120.2 83 4062.5 '+nbt)
 if 'summoned' not in reply.lower():raise RuntimeError(reply)

def apply(plan,rollback=False):
 log=BACKUP/'hall-decoration.json';added=[]
 if not rollback:
  if log.exists():raise RuntimeError('Journal exists; refusing accidental duplicate apply')
  log.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
 chunks=sorted({(e['pos'][0]//16,e['pos'][2]//16) for e in plan['edits']})
 try:
  for cx,cz in chunks:
   reply=console(f'execute in atlas:emerald run forceload query {cx*16} {cz*16}')
   if 'not marked' in reply.lower():
    console(f'execute in atlas:emerald run forceload add {cx*16} {cz*16}');added.append((cx,cz))
   elif 'marked' not in reply.lower():raise RuntimeError(reply)
  time.sleep(1)
  if rollback:
   console(f'execute in atlas:emerald run kill @e[tag={TAG}]')
   for e in reversed(plan['applied']):
    xyz=' '.join(map(str,e['pos']))
    reply=console(f'execute in atlas:emerald if block {xyz} {e["after"]["Name"]} run setblock {xyz} {state(e["before"])}')
    if 'changed' not in reply.lower():print('Rollback skipped changed/missing block:',xyz,reply,flush=True)
   console('save-all flush');print('Rollback restored guarded blocks and removed only project entities.');return
  # Preflight all original states in grouped, read-only commands.
  groups=batches(plan['edits'])
  for group in groups:
   checks=' '.join('if block '+' '.join(map(str,e['pos']))+' '+state(e['before']) for e in group)
   reply=console('execute in atlas:emerald '+checks)
   if 'passed' not in reply.lower():raise RuntimeError('Preflight: '+str(group[0]['pos'])+' '+reply)
  print('Preflight passed;',len(plan['edits']),'blocks.',flush=True)
  for i,group in enumerate(groups):
   for cmd in guarded(group):
    reply=console(cmd)
    if 'changed' not in reply.lower() and 'filled' not in reply.lower():raise RuntimeError('Placement: '+str(group[0]['pos'])+' '+reply)
   plan['applied'].extend(group)
   log.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
   if i%150==0:print('Applied',len(plan['applied']),'/',len(plan['edits']),flush=True)
  create_entities(plan)
  # Verification of structural blocks is exact. Neighbor-sensitive fence/stair shape and water states may legitimately update.
  for e in plan['edits']:
   xyz=' '.join(map(str,e['pos']));name=e['after']['Name']
   reply=console(f'execute in atlas:emerald if block {xyz} {name}')
   if 'passed' not in reply.lower():raise RuntimeError('Verification: '+xyz+' '+reply)
  console('save-all flush');plan['complete']=True;log.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
  print('Complete:',len(plan['edits']),'blocks;',len(plan['lamps']),'lanterns;',len(plan['labels']),'labels; project entities verified.',flush=True)
 except BaseException:
  if plan['applied']:
   print('Error; restoring project changes.',flush=True)
   console(f'execute in atlas:emerald run kill @e[tag={TAG}]')
   for e in reversed(plan['applied']):
    # Neighbor shapes change: match the block type, and restore recorded complete original state.
    xyz=' '.join(map(str,e['pos']))
    console(f'execute in atlas:emerald if block {xyz} {e["after"]["Name"]} run setblock {xyz} {state(e["before"])}')
   console('save-all flush');plan['rolled_back']=True;log.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
  raise
 finally:
  for cx,cz in added:console(f'execute in atlas:emerald run forceload remove {cx*16} {cz*16}')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args()
 plan=json.loads((BACKUP/'hall-decoration.json').read_text()) if a.rollback else make_plan()
 print('Plan:',len(plan['edits']),'blocks;',len(plan['lamps']),'lights;',len(plan['labels']),'labels.')
 if a.apply or a.rollback:apply(plan,a.rollback)
