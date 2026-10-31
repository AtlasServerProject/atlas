#!/usr/bin/env python3
"""Package shop-only Cobblemon machines on top of the installed recipe.1 Core, preserving all other deployed code."""
import hashlib,json,pathlib,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-recipe-cache-1.40.5-recipe.1/atlas-core-1.40.5+recipe.1.jar'
BUILD=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'atlas-core/build/libs/atlas-core-1.40.5+machines.1.jar'
VERSION='1.40.5+machines.1';STAGE=ROOT/'infra/releases/atlas-shop-machines-1.40.5-machines.1'
PREFIXES=['io/atlas/mixin/RestrictedRecipeMixin','io/atlas/modules/shopkeeper/model/ShopRestrictions']
FILES=set()
def allowed(n):return n in FILES or any(n==p+'.class' or n.startswith(p+'$') and n.endswith('.class') for p in PREFIXES)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE)==BASE.with_suffix('.jar.sha256').read_text().strip()
with zipfile.ZipFile(BASE) as z:original={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(BUILD) as z:replacement={n:z.read(n) for n in z.namelist() if allowed(n)}
assert all(p+'.class' in replacement for p in PREFIXES) and FILES<=set(replacement)
result=original|replacement;meta=json.loads(result['fabric.mod.json']);meta['version']=VERSION
result['fabric.mod.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
STAGE.mkdir(parents=True,exist_ok=True);out=STAGE/f'atlas-core-{VERSION}.jar'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in result.items():z.writestr(n,data)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 differences=[n for n in z.namelist() if n not in original or original[n]!=z.read(n)]
 assert all(n=='fabric.mod.json' or allowed(n) for n in differences)
 assert all(z.read(n)==data for n,data in original.items() if n!='fabric.mod.json' and not allowed(n))
out.with_suffix('.jar.sha256').write_text(sha(out)+'\n')
(STAGE/'verification.json').write_text(json.dumps({'version':VERSION,'baseSha256':sha(BASE),'sha256':sha(out),'changedEntries':differences,'prefixes':PREFIXES,'worldIdsUnchanged':True},indent=2)+'\n')
(STAGE/'NOTES.md').write_text('Shop-only Cobblemon machines: the crafting recipes of fossil analyzer, fossil monitor, healing machine, pasture, PC, restoration tank and TM machine are removed at recipe load, so the Atlas Mart is their only source. Migration 072 adds the monitor to the machines shop for 100.000 CobbleDollars without resale. Machines already placed or owned are untouched; Bottle Cap removal and the tag-recipe cache fix are unchanged. Only RestrictedRecipeMixin and ShopRestrictions differ from the installed recipe.1 release. No world/database edits.\n')
print(out)
