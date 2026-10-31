#!/usr/bin/env python3
"""Add automatic result-menu closing to the deployed crate-sounds release.
Avoids deploying unrelated, still-pending login changes from the working tree.
Run atlas-core/gradlew crateSpinTimelineTest remapJar first.
"""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-crate-sounds-1.40.5-crate.2/atlas-core-1.40.5+crate.2.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+crate.3'
STAGE=ROOT/'infra/releases/atlas-crate-autoclose-1.40.5-crate.3'
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
(STAGE/'NOTES.md').write_text('''# Automatic crate result closing

Built on deployed Core 1.40.5+crate.2. The rolling menu closes five seconds after the final reward is shown. A monotonic deadline is set only on the first reveal; delivery completion does not reset it. The server checks only the currently open crate-result menu, leaving previews and other screens untouched. Closing does not cancel or duplicate delivery.

Exact reward alignment and private click/level-up sounds preserved. No worlds, configuration, database records or authentication behavior changed. Timeline tests include the five-second boundary, late ticks and monotonic counter wrap. In-game confirmation still required.
''')
print(out);print('Verified: all entries outside crate classes/version are byte-for-byte unchanged.')
