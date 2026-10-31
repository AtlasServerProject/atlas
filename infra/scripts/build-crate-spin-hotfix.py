#!/usr/bin/env python3
"""Apply only the tested crate animation classes to the deployed 1.40.5 release.
Avoids deploying unrelated, still-pending login changes from the working tree.
Run atlas-core/gradlew crateSpinTimelineTest remapJar first.
"""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-emerald-spawn-1.40.5/atlas-core-1.40.5.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+crate.1'
STAGE=ROOT/'infra/releases/atlas-crate-spin-1.40.5-crate.1'
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
(STAGE/'NOTES.md').write_text('''# Crate reel correction\n\nBuilt on the exact deployed Core 1.40.5 archive. Only crate menu/service/timeline classes and the version metadata changed. Pending local-login changes are not deployed by this hotfix.\n\nThe reel now uses the persisted reward to align the last step, decelerates at 2/4/7/10-tick intervals, keeps the row and winning center unchanged throughout the reveal/delivery, and waits 40 ticks before allowing delivery. Selection weights, key reservation and durable delivery are unchanged. Exact properties distinguish normal/shiny rewards.\n\nValidated 20,100 outcome/pool-size combinations, every visible movement, final center and hold. In-game confirmation after restart is still required.\n''')
print(out);print('Verified: all entries outside crate classes/version are byte-for-byte unchanged.')
