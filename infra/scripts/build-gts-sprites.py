#!/usr/bin/env python3
"""Build Atlas Textures from the complete E19 pack and flat GTS models (no bitmap changes)."""
import argparse,hashlib,json,math,re,struct,zipfile,zlib
from pathlib import Path

def bounds(data):
    w,h=struct.unpack('>II',data[16:24]);depth,kind=data[24:26]
    if kind not in (3,6) or data[28]!=0:return w,h,(0,0,w,h)
    channels=4 if kind==6 else 1;stride=(w*channels*depth+7)//8;bpp=max(1,(channels*depth+7)//8)
    parts=[];alpha=b'';pos=8
    while pos<len(data):
        size=struct.unpack('>I',data[pos:pos+4])[0];key=data[pos+4:pos+8];body=data[pos+8:pos+8+size];pos+=12+size
        if key==b'IDAT':parts.append(body)
        elif key==b'tRNS':alpha=body
    raw=zlib.decompress(b''.join(parts));previous=bytearray(stride);xmin,ymin,xmax,ymax=w,h,0,0
    for y in range(h):
        f=raw[y*(stride+1)];row=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        for x in range(stride):
            a=row[x-bpp] if x>=bpp else 0;b=previous[x];c=previous[x-bpp] if x>=bpp else 0
            if f==1:row[x]=(row[x]+a)&255
            elif f==2:row[x]=(row[x]+b)&255
            elif f==3:row[x]=(row[x]+((a+b)//2))&255
            elif f==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);row[x]=(row[x]+(a if pa<=pb and pa<=pc else b if pb<=pc else c))&255
        for x in range(w):
            if kind==6:opacity=row[x*4+3]
            else:
                index=row[x] if depth==8 else (row[x//2]>>(4 if x%2==0 else 0))&15
                opacity=alpha[index] if index<len(alpha) else 255
            if opacity:xmin=min(xmin,x);ymin=min(ymin,y);xmax=max(xmax,x+1);ymax=max(ymax,y+1)
        previous=row
    return w,h,(xmin,ymin,xmax,ymax) if xmax>xmin else (0,0,w,h)

def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('index',type=Path);p.add_argument('--textures',type=Path,action='append',default=[]);p.add_argument('--icon',type=Path,default=Path(__file__).resolve().parents[1]/'templates/server-icon.png');args=p.parse_args()
    index=[];overrides=[]
    with zipfile.ZipFile(args.source) as source:
        variants=json.loads(source.read('assets/xaerominimap/entity/icon/definition/cobblemon/pokemon.json'))['variants']
        names=set(source.namelist());paths=sorted({v.split(':',1)[1] for v in variants.values() if 'assets/xaerominimap/entity/icon/sprite/'+v.split(':',1)[1] in names})
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
            def write(name,data):
                entry=zipfile.ZipInfo(name,(2026,10,12,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;out.writestr(entry,data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False,separators=(',',':')).encode())
            for name in sorted(names):
                if name.endswith('/') or name in {'pack.mcmeta','pack.png','CREDITS.txt'}: continue
                if name.startswith('/') or '..' in Path(name).parts: raise ValueError('Unsafe source path')
                write(name,source.read(name))
            for extra_path in args.textures:
                with zipfile.ZipFile(extra_path) as extra:
                    for name in sorted(extra.namelist()):
                        if name.endswith('/') or name in {'pack.mcmeta','pack.png','CREDITS.txt'}: continue
                        if name.startswith('/') or '..' in Path(name).parts or '\\' in name: raise ValueError('Unsafe texture path')
                        if name.startswith('assets/atlas_gts/') or name in {'assets/minecraft/models/item/paper.json','assets/minecraft/models/item/generated_paper.json'}: raise ValueError('Texture pack conflicts with reserved GTS models')
                        if name in out.namelist():
                            if out.read(name)!=extra.read(name): raise ValueError('Conflicting texture asset: '+name)
                            continue
                        write(name,extra.read(name))
            write('pack.png',args.icon.read_bytes())
            write('pack.mcmeta',{'pack':{'pack_format':34,'description':'Atlas Textures • Minimap, GTS e Cobblemon Interface'}})
            write('CREDITS.txt',b'Sprites copied without bitmap modification from the user-provided E19 Cobblemon Minimap Icons 1.4.4.\nE19 / Emery319; Pokemon sprites credited by E19 to MBCMechachu.\nhttps://modrinth.com/resourcepack/e19_cobblemon_minimap_icons\nCobblemon Interface 1.6.0 by VinnyStalck; MIT license preserved in LICENSE.md.\nAtlas additions: unified resource pack, GTS item models and sprite selection index.\n')
            for i,path in enumerate(paths,4000000):
                data=source.read('assets/xaerominimap/entity/icon/sprite/'+path);w,h,(x0,y0,x1,y1)=bounds(data)
                scale=min(3.9,0.92*min(w/max(1,x1-x0),h/max(1,y1-y0)))
                translate=[round((w/2-(x0+x1)/2)*16/w*scale,4),round(((y0+y1)/2-h/2)*16/h*scale,4),0]
                model=f'atlas_gts:item/{i}';texture=f'atlas_gts:item/{i}';write(f'assets/atlas_gts/textures/item/{i}.png',data)
                write(f'assets/atlas_gts/models/item/{i}.json',{'parent':'minecraft:item/generated','textures':{'layer0':texture},'display':{'gui':{'rotation':[0,0,0],'translation':translate,'scale':[round(scale,4),round(scale,4),1]}}})
                overrides.append({'predicate':{'custom_model_data':i},'model':model});index.append({'id':i,'path':path,'sha256':hashlib.sha256(data).hexdigest()})
            overrides.append({'predicate':{'custom_model_data':4000000+len(paths)},'model':'minecraft:item/generated_paper'})
            write('assets/minecraft/models/item/generated_paper.json',{'parent':'minecraft:item/generated','textures':{'layer0':'minecraft:item/paper'}})
            write('assets/minecraft/models/item/paper.json',{'parent':'minecraft:item/generated','textures':{'layer0':'minecraft:item/paper'},'overrides':overrides})
    args.index.parent.mkdir(parents=True,exist_ok=True);args.index.write_text(json.dumps(index,separators=(',',':')))
    print('GTS sprites:',len(index),'ZIP bytes:',args.output.stat().st_size,'SHA1:',hashlib.sha1(args.output.read_bytes()).hexdigest())
if __name__=='__main__':main()
