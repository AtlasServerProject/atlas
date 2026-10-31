#!/usr/bin/env python3
"""Read-only Anvil/NBT inspection. Never writes Minecraft world data."""
import io,struct,zlib,pathlib,json,math,functools
class NBT:
 def __init__(self,data):self.f=io.BytesIO(data)
 def take(self,n):
  b=self.f.read(n)
  if len(b)!=n:raise ValueError('Truncated NBT')
  return b
 def number(self,fmt):return struct.unpack('>'+fmt,self.take(struct.calcsize('>'+fmt)))[0]
 def string(self):return self.take(self.number('H')).decode('utf-8',errors='replace')
 def payload(self,t):
  if t in {1,2,3,4,5,6}:return self.number({1:'b',2:'h',3:'i',4:'q',5:'f',6:'d'}[t])
  if t==7:return self.take(self.number('i'))
  if t==8:return self.string()
  if t==9:
   item=self.number('B');return [self.payload(item) for _ in range(self.number('i'))]
  if t==10:
   d={}
   while (tag:=self.number('B'))!=0:
    name=self.string();d[name]=self.payload(tag)
   return d
  if t in {11,12}:return [self.number('i' if t==11 else 'q') for _ in range(self.number('i'))]
  raise ValueError('Unknown NBT tag '+str(t))
 def root(self):
  tag=self.number('B');self.string();return self.payload(tag)
class Region:
 def __init__(self,path):self.data=pathlib.Path(path).read_bytes()
 @functools.lru_cache(maxsize=1024)
 def chunk(self,cx,cz):
  n=(cx%32+(cz%32)*32)*4;offset=int.from_bytes(self.data[n:n+3],'big')*4096
  if not offset:return None
  length=int.from_bytes(self.data[offset:offset+4],'big');kind=self.data[offset+4];raw=self.data[offset+5:offset+4+length]
  if kind==2:raw=zlib.decompress(raw)
  elif kind!=3:raise ValueError('Unsupported chunk compression')
  return NBT(raw).root()
 def block(self,x,y,z):
  chunk=self.chunk(x//16,z//16)
  if chunk is None:return None
  section=next((s for s in chunk.get('sections',[]) if s['Y']==y//16),None)
  if not section or 'block_states' not in section:return {'Name':'minecraft:air'}
  states=section['block_states'];palette=states['palette']
  if len(palette)==1:return palette[0]
  bits=max(4,(len(palette)-1).bit_length());per=64//bits;i=(y%16)*256+(z%16)*16+x%16
  index=(states['data'][i//per]>>((i%per)*bits))&((1<<bits)-1)
  return palette[index]
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('region');p.add_argument('x',type=int);p.add_argument('y',type=int);p.add_argument('z',type=int);a=p.parse_args()
 print(json.dumps(Region(a.region).block(a.x,a.y,a.z)))
