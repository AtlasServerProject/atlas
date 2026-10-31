#!/usr/bin/env python3
"""Package the EV corrals and the Shopping VIP on top of the installed luz.1 Core, preserving all other deployed code."""
import hashlib,json,pathlib,re,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-light-command-1.40.5-luz.1/atlas-core-1.40.5+luz.1.jar'
BUILD=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'atlas-core/build/libs/atlas-core-1.40.5+evvip.1.jar'
VERSION='1.40.5+evvip.1';STAGE=ROOT/'infra/releases/atlas-ev-vip-1.40.5-evvip.1'
PREFIXES=['io/atlas/AtlasMod','io/atlas/bootstrap/AtlasBootstrap','io/atlas/commands/EvCorralCommand',
 'io/atlas/modules/evcorral/EvCorralModule','io/atlas/modules/evcorral/config/EvCorralConfig','io/atlas/modules/evcorral/service/EvCorralService',
 'io/atlas/modules/shopkeeper/model/ShopRestrictions','io/atlas/modules/shopkeeper/repository/ShopkeeperRepository','io/atlas/modules/shopkeeper/service/ShopCatalogue','io/atlas/modules/shopkeeper/service/ShopkeeperService']
FILES=set()
def allowed(n):return n in FILES or any(n==p+'.class' or n.startswith(p+'$') and n.endswith('.class') for p in PREFIXES)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE)==BASE.with_suffix('.jar.sha256').read_text().strip()
with zipfile.ZipFile(BASE) as z:original={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(BUILD) as z:replacement={n:z.read(n) for n in z.namelist() if allowed(n)}
assert all(p+'.class' in replacement for p in PREFIXES) and FILES<=set(replacement)
result=original|replacement;meta=json.loads(result['fabric.mod.json']);meta['version']=VERSION
result['fabric.mod.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
# Every Atlas class referenced by a copied class must exist in the result (catches undeployed branch code).
for n in replacement:
 for ref in set(re.findall(rb'io/atlas/[A-Za-z0-9_/$]+',replacement[n])):
  name=ref.decode().rstrip('$')
  assert name+'.class' in result or any(k.startswith(name+'/') for k in result),f'{n} references missing {name}'
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
(STAGE/'NOTES.md').write_text('''EV corrals and Shopping VIP.
- Currais de EV: new module. Reads config/atlas/ev-corrals.json (written by infra/world-tools/warp-schematics.py --vip-origin X Y Z --vip-world W after the VIP warp is pasted); without the file it stays off. Keeps up to 4 uncatchable wild Pokemon (level 30-50) with the best single-stat EV yield in each of the six domes, refills 20 s after a defeat while a player is within 48 blocks, puts escapees back and removes other wild Pokemon inside a dome. Admin: /currais (status), /currais recarregar.
- Shopping VIP: NPCs tagged atlas_npc_vip_store_1..4 sell the VIP-only items (balls and caps, mints, form items, mega stones and Z crystals). VIP 1+ only, any world; sell-back disabled. Offers are added once (catalogue version shopping-vip-1) with ON CONFLICT DO NOTHING: existing offers, prices and staff edits are untouched. Prices come from ShopRestrictions.vipPrice and can be edited in npc_shop_offers, then /lojistas atualizar.
No world or schema edits.
''')
print(out)
