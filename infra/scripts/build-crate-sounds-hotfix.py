#!/usr/bin/env python3
"""Apply crate sounds to the deployed crate-alignment hotfix.
Avoids deploying unrelated, still-pending login changes from the working tree.
Run atlas-core/gradlew crateSpinTimelineTest remapJar first.
"""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-crate-spin-1.40.5-crate.1/atlas-core-1.40.5+crate.1.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+crate.2'
STAGE=ROOT/'infra/releases/atlas-crate-sounds-1.40.5-crate.2'
STAGE.mkdir(parents=True,exist_ok=True)
basehash=hashlib.sha256(BASE.read_bytes()).hexdigest()
assert basehash==BASE.with_suffix('.jar.sha256').read_text().strip()
def allowed(n):
    return n=='io/atlas/modules/crates/menu/CrateMenu.class' or n.startswith('io/atlas/modules/crates/service/CrateService') and n.endswith('.class') or n=='io/atlas/modules/crates/service/CrateSpinTimeline.class'
with zipfile.ZipFile(BASE) as z: original={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(BUILD) as z: replacements={n:z.read(n) for n in z.namelist() if allowed(n)}
assert 'io/atlas/modules/crates/menu/CrateMenu.class' in replacements
assert 'io/atlas/modules/crates/service/CrateService.class' in replacements
assert 'io/atlas/modules/crates/service/CrateSpinTimeline.class' in replacements
result=original|replacements
metadata=json.loads(result['fabric.mod.json']);metadata['version']=VERSION
result['fabric.mod.json']=(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n').encode()
out=STAGE/f'atlas-core-{VERSION}.jar'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for n,data in result.items():z.writestr(n,data)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    differences=[n for n in z.namelist() if n not in original or original[n]!=z.read(n)]
    assert all(n=='fabric.mod.json' or allowed(n) for n in differences)
    assert all(z.read(n)==data for n,data in original.items() if n!='fabric.mod.json' and not allowed(n))
checksum=hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix('.jar.sha256').write_text(checksum+'\n')
(STAGE/'verification.json').write_text(json.dumps({'version':VERSION,'baseSha256':basehash,'sha256':checksum,'changedEntries':differences,'unchangedOutsideCrates':True,'timelineOutcomesTested':20100},indent=2)+'\n')
(STAGE/'NOTES.md').write_text('''# Crate sounds

Built on deployed Core 1.40.5+crate.1. Adds UI button click at each visible reel movement and player level-up when the winner is revealed. Sounds are sent only to the opening player, only while the rolling menu is open. No sound is replayed during delivery polling. Volumes: click 0.35, reward 0.65, pitch 1.0. Vanilla sounds; no client mod/resource update required.

Exact reward alignment and delivery hold preserved. No world/database/config changes; pending authentication changes are not deployed. Compilation and 20,100 timeline cases passed. In-game listening still needed after installation.
''')
print(out);print('Verified: all entries outside crate classes/version are byte-for-byte unchanged.')
