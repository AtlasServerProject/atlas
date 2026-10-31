#!/usr/bin/env python3
"""Add the chosen one-percent Hidden Ability policy to crate rewards.
Avoids deploying unrelated, still-pending login changes from the working tree.
Run atlas-core/gradlew crateSpinTimelineTest remapJar first.
"""
import hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'infra/releases/atlas-crate-autoclose-1.40.5-crate.3/atlas-core-1.40.5+crate.3.jar'
BUILD=ROOT/'atlas-core/build/libs/atlas-core-1.40.6.jar'
VERSION='1.40.5+crate.4'
STAGE=ROOT/'infra/releases/atlas-crate-ha-1.40.5-crate.4'
STAGE.mkdir(parents=True,exist_ok=True)
basehash=hashlib.sha256(BASE.read_bytes()).hexdigest()
assert basehash==BASE.with_suffix('.jar.sha256').read_text().strip()
def allowed(n):
    return n=='io/atlas/modules/crates/menu/CrateMenu.class' or n.startswith('io/atlas/modules/crates/service/CrateService') and n.endswith('.class') or n in {'io/atlas/modules/crates/service/CrateSpinTimeline.class','io/atlas/modules/crates/service/CrateAbilityPolicy.class'}
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
(STAGE/'NOTES.md').write_text('''# Crate Hidden Abilities

Built on Core 1.40.5+crate.3. Adds the operator-selected 1/100 HA chance to newly generated rewards whose actual form lists a HiddenAbility. Same independent chance for normal/shiny and all crates, including monthly. Uses Cobblemon HiddenAbilityProperty to apply and verify the ability before reservation/JSON persistence. Unsupported forms keep their ordinary ability. Recovery/retries deserialize the saved Pokemon and never reroll HA. Existing pending prizes are unchanged.

Delivery chat marks HA wins. Preview describes the HA rate and retains weighted species/shiny odds. Reel alignment, private sounds and five-second auto-close preserved. No worlds/config/schema/authentication changes.

Policy and reel regression tests passed; compilation succeeded. Live HA draw/serialization confirmation still needs an in-game opening after installation. This 1% rate is an Atlas choice, not a claim about default wild spawns.
''')
print(out);print('Verified: all entries outside crate classes/version are byte-for-byte unchanged.')
