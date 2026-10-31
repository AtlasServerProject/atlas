#!/usr/bin/env python3
"""Package transparent key art with tightly framed UVs and larger inventory icons.
This script reads alpha bounds; it does not modify/repaint the image pixels.
Run with the atlas-world-tools Python environment (Pillow).
"""
from pathlib import Path
from PIL import Image
import argparse,hashlib,io,json,zipfile
root=Path(__file__).resolve().parents[3];packs=root/'infra/resourcepacks'
p=argparse.ArgumentParser();p.add_argument('--art',required=True,type=Path);a=p.parse_args()
base=packs/'atlas-textures-f2e99dd48aab65f6.zip'
with zipfile.ZipFile(base) as z:entries={n:z.read(n) for n in z.namelist()}
for i in range(1,11):
 identifier=f'generation_{i}' if i<10 else 'legendary_monthly'
 path=a.art/(identifier+'.png');raw=path.read_bytes()
 image=Image.open(io.BytesIO(raw)).convert('RGBA');alpha=image.getchannel('A')
 if alpha.getextrema()!=(0,255):raise ValueError('Missing real transparency: '+identifier)
 bounds=alpha.point(lambda x:255 if x>24 else 0).getbbox()
 if not bounds:raise ValueError('Empty key art: '+identifier)
 w,h=image.size;x0,y0,x1,y1=bounds
 # UV crops transparent margins without altering the source image.
 x0=max(0,x0-2);y0=max(0,y0-2);x1=min(w,x1+2);y1=min(h,y1+2)
 ratio=(x1-x0)/(y1-y0);width=min(15.8,15.8*ratio);height=min(15.8,15.8/ratio)
 uv=[x0/w*16,y0/h*16,x1/w*16,y1/h*16]
 entries[f'assets/atlas/textures/item/keys/{identifier}.png']=raw
 model={'textures':{'key':f'atlas:item/keys/{identifier}','particle':f'atlas:item/keys/{identifier}'},'gui_light':'front','elements':[{'from':[8-width/2,8-height/2,8],'to':[8+width/2,8+height/2,8],'faces':{'south':{'uv':uv,'texture':'#key'},'north':{'uv':[uv[2],uv[1],uv[0],uv[3]],'texture':'#key'}}}],'display':{'gui':{'rotation':[0,0,0],'translation':[0,0,0],'scale':[1,1,1]},'fixed':{'rotation':[0,0,0],'scale':[1,1,1]}}}
 entries[f'assets/atlas/models/item/keys/{identifier}.json']=json.dumps(model).encode()
 print(identifier,'alpha bounds',bounds,'item size',round(width,2),round(height,2))
entries['pack.mcmeta']=json.dumps({'pack':{'pack_format':34,'description':'Atlas Textures • Chaves ampliadas e transparentes • Minecraft 1.21.1'}}).encode()
entries['atlas-keys.json']=json.dumps({'customModelData':{f'generation_{i}' if i<10 else 'legendary_monthly':880100+i for i in range(1,11)},'source':'Transparent-background cutouts of website key illustrations; tightly framed UVs; 15.8-unit maximum size.'}).encode()
tmp=packs/'atlas-transparent-keys-build.zip'
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(entries.items()):z.writestr(n,b)
sha=hashlib.sha1(tmp.read_bytes()).hexdigest();target=packs/f'atlas-textures-{sha[:16]}.zip';tmp.replace(target)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
metadata={'file':str(target),'sha1':sha,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size}
(packs/'transparent-keys-release.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata))
