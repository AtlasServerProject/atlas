#!/usr/bin/env python3
"""Reuse unchanged website PNGs, mapping portrait/cropped UVs in item models."""
from pathlib import Path
import hashlib,json,struct,zipfile
root=Path(__file__).resolve().parents[3]
packs=root/'infra/resourcepacks';web=root/'atlas-web/public/keys'
base=packs/'atlas-textures-554668c6ade11b52.zip'
images=['generation-1-cartoon.png','generation-2-thematic.png','johto-hoenn-cartoon.png','generation-4-arceus-cartoon.png',*[f'generation-{i}-cartoon.png' for i in range(5,10)],'monthly-cartoon.png']
entries={};overrides=[]
for i,name in enumerate(images,1):
 identifier=f'generation_{i}' if i<=9 else 'legendary_monthly'
 raw=(web/name).read_bytes();w,h=struct.unpack('>II',raw[16:24]);left=8 if i==3 else 0
 ratio=(w/2 if i==3 else w)/h
 width=min(14,14*ratio);height=min(14,14/ratio)
 entries[f'assets/atlas/textures/item/keys/{identifier}.png']=raw
 model={'textures':{'key':f'atlas:item/keys/{identifier}','particle':f'atlas:item/keys/{identifier}'},'gui_light':'front','elements':[{'from':[8-width/2,8-height/2,8],'to':[8+width/2,8+height/2,8],'faces':{'south':{'uv':[left,0,16,16],'texture':'#key'},'north':{'uv':[16,0,left,16],'texture':'#key'}}}],'display':{'gui':{'rotation':[0,0,0],'translation':[0,0,0],'scale':[1,1,1]},'fixed':{'rotation':[0,0,0],'scale':[1,1,1]}}}
 entries[f'assets/atlas/models/item/keys/{identifier}.json']=json.dumps(model).encode()
 overrides.append({'predicate':{'custom_model_data':880100+i},'model':f'atlas:item/keys/{identifier}'})
entries['assets/minecraft/models/item/tripwire_hook.json']=json.dumps({'parent':'minecraft:item/generated','textures':{'layer0':'minecraft:item/tripwire_hook'},'overrides':overrides}).encode()
with zipfile.ZipFile(base) as old:
 entries.update({n:old.read(n) for n in old.namelist() if n not in entries and n!='pack.mcmeta'})
entries['pack.mcmeta']=json.dumps({'pack':{'pack_format':34,'description':'Atlas Textures • Chaves ilustradas • Minecraft 1.21.1 / Cobblemon 1.8.2'}}).encode()
entries['atlas-keys.json']=json.dumps({'customModelData':{f'generation_{i}' if i<10 else 'legendary_monthly':880100+i for i in range(1,11)},'source':'Same unchanged artwork as Atlas website; Hoenn uses the right half by model UV.'}).encode()
tmp=packs/'atlas-keys-build.zip'
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(entries.items()):z.writestr(n,b)
sha=hashlib.sha1(tmp.read_bytes()).hexdigest();target=packs/f'atlas-textures-{sha[:16]}.zip';tmp.replace(target)
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for n in z.namelist():
  if n.endswith('.json') or n=='pack.mcmeta':json.loads(z.read(n))
 assert len(json.loads(z.read('assets/minecraft/models/item/tripwire_hook.json'))['overrides'])==10
print(json.dumps({'file':str(target),'sha1':sha,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size}))
