#!/usr/bin/env python3
"""Package Lobby display-name standardization, preserving all other deployed code."""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-professors-dialogue-1.40.5-hall.1/atlas-core-1.40.5+hall.1.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+lobby.2';STAGE=ROOT/'infra/releases/atlas-lobby-interaction-1.40.5-lobby.2'
PREFIXES=['io/atlas/modules/lobby/listener/LobbyProtectionListener','io/atlas/mixin/ProfessionBlockPlacementMixin','io/atlas/commands/RandomTeleportCommand']
def allowed(n):return any(n==p+'.class' or n.startswith(p+'$') and n.endswith('.class') for p in PREFIXES)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE)==BASE.with_suffix('.jar.sha256').read_text().strip()
with zipfile.ZipFile(BASE) as z:original={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(BUILD) as z:replacement={n:z.read(n) for n in z.namelist() if allowed(n)}
assert all(p+'.class' in replacement for p in PREFIXES)
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
(STAGE/'NOTES.md').write_text('Lobby interaction fix: block placement is denied at BlockItem.place instead of cancelling all block interactions while holding a BlockItem. Crafting-table and healer native interaction stays available; breaking/placement authorization, auth/rules/moderation guards and Bottle Cap recipe restrictions remain. Adds console-only read-only atlasplayerdiagnose <player> to inspect RTP/inventory conditions and oak-planks recipe availability. Only three class prefixes differ from the installed hall.1 release. No world/database edits.\n')
print(out)
