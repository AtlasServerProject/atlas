#!/usr/bin/env python3
"""Read-only resource inventory. Presence is not a native battle certification."""
import json,re,zipfile
from pathlib import Path
root=Path('/home/somente/dev/atlas');mods=Path('/opt/atlas/server/fabric/mods')
species={};modlist=[]
def ident(s):return re.sub('[^a-z0-9]','',s.lower())
for jar in sorted(mods.glob('*.jar')):
 modlist.append({'file':jar.name,'bytes':jar.stat().st_size})
 with zipfile.ZipFile(jar) as z:
  for name in z.namelist():
   if not name.startswith('data/') or '/species/' not in name or not name.endswith('.json'):continue
   try:d=json.loads(z.read(name))
   except Exception:continue
   if not isinstance(d,dict) or not d.get('name'):continue
   key=ident(d['name']);entry=species.setdefault(key,{'name':d['name'],'definitions':[],'forms':[]})
   entry['definitions'].append({'mod':jar.name,'implemented':d.get('implemented',False),'baseStats':d.get('baseStats',{})})
   for f in d.get('forms',[]):
    if isinstance(f,dict):entry['forms'].append({'name':f.get('name',''),'candidateId':ident(d['name']+f.get('name','')),'baseStats':f.get('baseStats',{}),'mod':jar.name})
# Additive species resources can mark base species implemented or add forms.
for jar in sorted(mods.glob('*.jar')):
 with zipfile.ZipFile(jar) as z:
  for name in z.namelist():
   if '/species_additions/' not in name or not name.endswith('.json'):continue
   try:d=json.loads(z.read(name))
   except Exception:continue
   if not isinstance(d,dict) or not isinstance(d.get('target'),str):continue
   key=ident(d['target'].split(':')[-1]);entry=species.get(key)
   if not entry:continue
   if 'implemented' in d:entry['definitions'].append({'mod':jar.name,'implemented':d['implemented'],'source':'species_additions','baseStats':d.get('baseStats',{})})
   for f in d.get('forms',[]):
    if isinstance(f,dict):entry['forms'].append({'name':f.get('name',''),'candidateId':ident(entry['name']+f.get('name','')),'baseStats':f.get('baseStats',{}),'mod':jar.name})
items=json.loads((root/'atlas-api/.runtime/cobblemon-182-audit/audit-item-registry.json').read_text())
result={'scope':'Installed mod resource declarations; item registry from previous isolated native audit. No claims of native mechanics equivalence.','species':species,'registeredItemIds':items,'installedMods':modlist,'itemRegistryOrigin':'isolated Cobblemon 1.8.2 audit; earlier runtime snapshot, not reloaded in production','datapackOverridesAudited':False}
out=root/'atlas-bot/.runtime/gen8-audit/resources.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print('Resource declarations:',len(species),'species; prior native registry:',len(items),'items')
