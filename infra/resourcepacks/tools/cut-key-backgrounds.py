#!/usr/bin/env python3
"""Deterministic navy-background cutouts, explicitly requested by the user.
Preserves original RGB pixels; only alpha, framing and Hoenn panel selection change.
"""
from pathlib import Path
from PIL import Image
import numpy as np
from scipy import ndimage
import json,hashlib
root=Path(__file__).resolve().parents[3];source=root/'atlas-web/public/keys';output=root/'infra/resourcepacks/key-art-transparent';output.mkdir(parents=True,exist_ok=True)
images=['generation-1-cartoon.png','generation-2-thematic.png','johto-hoenn-cartoon.png','generation-4-arceus-cartoon.png',*[f'generation-{i}-cartoon.png' for i in range(5,10)],'monthly-cartoon.png']
report=[]
for i,name in enumerate(images,1):
 identifier=f'generation_{i}' if i<10 else 'legendary_monthly'
 original=Image.open(source/name).convert('RGBA')
 if i==3:original=original.crop((original.width//2,0,original.width,original.height))
 pixels=np.array(original);rgb=pixels[:,:,:3].astype(np.int16);r,g,b=np.moveaxis(rgb,-1,0)
 # Navy backdrop occupies this restricted hue/lightness range. Black linework,
 # light blues, purple, teal, white and colored character surfaces are retained.
 candidate=(r<=24)&(g>=8)&(g<=40)&(b>=32)&(b<=88)&(b-r>=27)&(b-g>=18)
 labels,count=ndimage.label(candidate)
 sizes=np.bincount(labels.ravel());remove=sizes>=100;remove[0]=False
 boundary=np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])));remove[boundary[boundary!=0]]=True
 mask=remove[labels]
 pixels[:,:,3][mask]=0
 # Preserve ALL original color pixels, including the opaque outline.
 assert np.array_equal(pixels[:,:,:3],np.array(original)[:,:,:3])
 image=Image.fromarray(pixels);bounds=image.getchannel('A').getbbox()
 if not bounds:raise RuntimeError('Empty image '+identifier)
 x0,y0,x1,y1=bounds;pad=8;image=image.crop((max(0,x0-pad),max(0,y0-pad),min(image.width,x1+pad),min(image.height,y1+pad)))
 path=output/(identifier+'.png');image.save(path,optimize=True)
 report.append({'identifier':identifier,'source':name,'sourceSha256':hashlib.sha256((source/name).read_bytes()).hexdigest(),'outputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dimensions':image.size,'removedPixels':int(mask.sum()),'removedPercent':round(mask.mean()*100,2),'originalRgbPreserved':True})
 print(identifier,image.size,round(mask.mean()*100,1),'percent transparent')
(output/'cutout-report.json').write_text(json.dumps(report,indent=2)+'\n')
