#!/usr/bin/env python3
"""Package only Atlas warps and their two registration points onto the deployed Core."""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-crate-ha-1.40.5-crate.4/atlas-core-1.40.5+crate.4.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+warp.1'
STAGE=ROOT/'infra/releases/atlas-warps-1.40.5-warp.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def allowed(n):return n in {'io/atlas/AtlasMod.class','io/atlas/bootstrap/AtlasBootstrap.class'} or n.startswith('io/atlas/modules/warp/') or n.startswith('io/atlas/commands/WarpCommands')
assert sha(BASE)==BASE.with_suffix('.jar.sha256').read_text().strip()
with zipfile.ZipFile(BASE) as z:original={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(BUILD) as z:replacements={n:z.read(n) for n in z.namelist() if n.endswith('.class') and allowed(n)}
for required in ['io/atlas/AtlasMod.class','io/atlas/bootstrap/AtlasBootstrap.class','io/atlas/commands/WarpCommands.class','io/atlas/modules/warp/WarpModule.class','io/atlas/modules/warp/model/Warp.class','io/atlas/modules/warp/repository/WarpStore.class','io/atlas/modules/warp/service/WarpService.class','io/atlas/modules/warp/menu/WarpsMenu.class']:assert required in replacements,required
result=original|replacements
metadata=json.loads(result['fabric.mod.json']);metadata['version']=VERSION
result['fabric.mod.json']=(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n').encode()
STAGE.mkdir(parents=True,exist_ok=True);out=STAGE/f'atlas-core-{VERSION}.jar'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for n,data in result.items():z.writestr(n,data)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    differences=[n for n in z.namelist() if n not in original or original[n]!=z.read(n)]
    assert all(n=='fabric.mod.json' or allowed(n) for n in differences)
    assert all(z.read(n)==data for n,data in original.items() if n!='fabric.mod.json' and not allowed(n))
out.with_suffix('.jar.sha256').write_text(sha(out)+'\n')
(STAGE/'verification.json').write_text(json.dumps({'version':VERSION,'baseSha256':sha(BASE),'sha256':sha(out),'changedEntries':differences,'preservesUnrelatedClasses':True,'warpStoreTestPassed':True,'inGameTested':False},indent=2)+'\n')
(STAGE/'NOTES.md').write_text((ROOT/'infra/warps/README.md').read_text())
print(out);print('Verified: original crate fixes and all unrelated classes preserved byte-for-byte.')
