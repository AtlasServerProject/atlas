#!/usr/bin/env python3
"""Decorate the existing stadium using the guarded, journaled console editor."""
import argparse,importlib.util,json,pathlib
ROOT=pathlib.Path('/home/somente/dev/atlas')
s=importlib.util.spec_from_file_location('editor',ROOT/'infra/world-tools/decorate-professors-hall.py');e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
BACKUP=pathlib.Path('/home/somente/backups/lobby-emerald/arena-20261030T185516Z')
e.BACKUP=BACKUP;e.TAG='atlas_arena_decoration'
def make_plan():
 regions={i:e.region.Region(BACKUP/f'region/r.2.{i}.mca') for i in [7,8]};edits=[];labels=[];lamps=[]
 def old(x,y,z):return regions[z//512].block(x,y,z)
 def put(x,y,z,name,expected='minecraft:air',**props):
  before=old(x,y,z)
  if before['Name']!=expected:raise ValueError((x,y,z,before,expected))
  edits.append({'pos':[x,y,z],'before':before,'after':e.block(name,**props)})
 def label(text,x,y,z,scale=.55):labels.append({'text':text,'pos':[x,y,z],'scale':scale})
 # Two trainer platforms, without touching the central Poké Ball mosaic or white boundary.
 for cx,color in [(1123,'cyan'),(1139,'red')]:
  for x in range(cx-1,cx+2):
   for z in range(4108,4111):
    put(x,82,z,'smooth_quartz',expected='minecraft:grass_block')
    put(x,83,z,color+'_carpet')
 # Embedded floor illumination along clear entrance corridors, with Atlas trim.
 for cx in [1108,1112,1116,1148,1152,1156]:
  for z in [4107,4111]:
   put(cx,82,z,'sea_lantern',expected='minecraft:polished_andesite')
 for x in range(1148,1158):
  for z in [4106,4112]:put(x,82,z,'cyan_concrete',expected='minecraft:polished_andesite')
 # Framed trophy niches on the two sides of the east entrance (outside the passage).
 for z in [4104,4114]:
  for y in [83,84]:put(1157,y,z,'polished_blackstone',expected='minecraft:white_concrete')
  put(1156,83,z,'chiseled_quartz_block',expected='minecraft:white_concrete')
  put(1156,84,z,'gold_block',expected='minecraft:white_concrete')
  put(1156,85,z,'amethyst_cluster',expected='minecraft:white_concrete',facing='up',waterlogged=False)
 # Cyan/blue details in existing seating fascia, keeping the red rows and all aisles.
 for x in range(1116,1145):
  for z in [4088,4130]:
   # Only white structural fascia; never grass, steps, glass or the field.
   if old(x,84,z)['Name']=='minecraft:white_concrete':put(x,84,z,'cyan_concrete',expected='minecraft:white_concrete')
 # Light brackets: anchored to existing red tunnel ceilings, safely above head height.
 for x in [1150,1154]:
  for z in [4106,4112]:
   roof=next((y for y in range(87,112) if old(x,y,z)['Name']!='minecraft:air'),None)
   if roof is None:raise ValueError('No ceiling')
   for y in range(roof-1,roof-3,-1):put(x,y,z,'chain',axis='y',waterlogged=False)
   put(x,roof-3,z,'lantern',hanging=True,waterlogged=False);lamps.append([x,roof-3,z])
 label('ARENA ATLAS',1157.2,87.3,4109.5,.85)
 label('Prepare sua equipe. Escreva sua história.',1155,85.8,4109.5,.32)
 label('CAMPO DE BATALHA',1130,96,4109,.6)
 label('TREINADOR AZUL',1123,85.8,4109,.32)
 label('TREINADOR VERMELHO',1139,85.8,4109,.32)
 label('ARQUIBANCADA',1130,93,4128,.4)
 label('Respeite seu adversário • Jogue com fair play',1130,91.7,4128,.27)
 assert len({tuple(i['pos']) for i in edits})==len(edits)
 return {'dimension':'atlas:emerald','backup':str(BACKUP),'tag':e.TAG,'edits':edits,'labels':labels,'lamps':lamps,'applied':[]}
def entities(plan):
 for i,l in enumerate(plan['labels']):
  text=json.dumps(json.dumps({'text':l['text'],'color':'#73E7FF','bold':True},ensure_ascii=False),ensure_ascii=False)
  scale=l['scale'];xyz=' '.join(map(str,l['pos']))
  nbt='{Tags:["'+e.TAG+'"],text:'+text+',billboard:"center",alignment:"center",background:0,shadow:1b,see_through:0b,line_width:420,view_range:1.3f,brightness:{block:15,sky:15},transformation:{translation:[0f,0f,0f],left_rotation:[0f,0f,0f,1f],scale:['+','.join([str(scale)+'f']*3)+'],right_rotation:[0f,0f,0f,1f]}}'
  reply=e.console(f'execute in atlas:emerald run summon minecraft:text_display {xyz} {nbt}')
  if 'summoned' not in reply.lower():raise RuntimeError(reply)
e.create_entities=entities
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args()
 plan=json.loads((BACKUP/'hall-decoration.json').read_text()) if a.rollback else make_plan()
 print('Arena decoration:',len(plan['edits']),'guarded block changes;',len(plan['labels']),'signs.')
 if a.apply or a.rollback:e.apply(plan,a.rollback)
