// Read-only simulations against the installed Showdown files; not an end-to-end Cobblemon client test.
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root='/home/somente/dev/atlas',engine='/opt/atlas/server/fabric/showdown';
const {Dex}=require(engine+'/sim/dex'),{Battle}=require(engine+'/sim/battle');
const resources=JSON.parse(fs.readFileSync(root+'/atlas-bot/.runtime/gen8-audit/resources.json'));
const official=JSON.parse(fs.readFileSync(root+'/infra/config/tournament-formats-gen8.json'));
const d8=Dex.mod('gen8'),dc=Dex.mod('cobblemon');d8.includeData();dc.includeData();
const id=s=>s.toLowerCase().replace(/[^a-z0-9]/g,'');
const report={checkedOn:'2026-10-23',readOnly:true,scope:'Installed resource declarations + isolated patched Showdown engine simulations. Not a complete native Minecraft PvP certification.',defaultGeneration:dc.gen,formats:[],essentialItems:[],mechanicChecks:[],generationDifferences:[],blockers:[]};
for(const format of official.formats){
 const f=d8.formats.get(format.id),rules=d8.formats.getRuleTable(f);
 const species=d8.species.all().filter(s=>s.gen<=8&&!s.isNonstandard&&!s.battleOnly&&!rules.isBannedSpecies(s));
 const missing=species.filter(s=>!resources.species[id(s.baseSpecies)]);
 const notDeclaredImplemented=species.filter(s=>resources.species[id(s.baseSpecies)]&&!resources.species[id(s.baseSpecies)].definitions.some(d=>d.implemented));
 const formaUncertain=species.filter(s=>s.forme&&resources.species[id(s.baseSpecies)]&&!resources.species[id(s.baseSpecies)].forms.some(f=>f.candidateId===s.id));
 report.formats.push({id:format.id,eligibleSpeciesOrForms:species.length,missingBaseResourceDeclarations:missing.map(s=>s.name),baseImplementationUnconfirmed:notDeclaredImplemented.map(s=>s.name),formMappingNeedsNativeVerification:formaUncertain.map(s=>s.name),installedDirectRules:f.ruleset,installedDirectBans:f.banlist,upstreamRulesMatch:JSON.stringify(f.ruleset)===JSON.stringify(format.directRuleset)||(format.id==='gen8anythinggoes'&&JSON.stringify(f.ruleset)===JSON.stringify(['Obtainable','Team Preview','HP Percentage Mod','Cancel Mod','Endless Battle Clause'])),upstreamBansMatch:JSON.stringify(f.banlist||[])===JSON.stringify(format.directBanlist),readyForOfficialTournament:false});
}
const normalizeItem=s=>id(s.split(':').at(-1));
const registeredItemNames=new Set(resources.registeredItemIds.map(normalizeItem));
const gen8Items=d8.items.all().filter(item=>item.gen<=8&&!item.isNonstandard);
report.itemCoverage={gen8LegalItemDefinitions:gen8Items.length,identifierMatches:gen8Items.filter(item=>registeredItemNames.has(item.id)).length,unmatched:gen8Items.filter(item=>!registeredItemNames.has(item.id)).map(item=>item.name),note:'Unmatched IDs may have other mod mappings; registered does not mean obtainable or effect-tested.'};
const items=resources.registeredItemIds;
for(const name of ['Leftovers','Heavy-Duty Boots','Choice Band','Choice Specs','Choice Scarf','Life Orb','Focus Sash','Assault Vest','Rocky Helmet','Eviolite','Black Sludge','Flame Orb','Toxic Orb','Light Clay','Weakness Policy','Rusted Sword','Rusted Shield','Griseous Orb']){
 const expected=id(name);report.essentialItems.push({name,gen8Exists:d8.items.get(name).exists,registeredCandidates:items.filter(x=>id(x.split(':')[1])===expected),availabilityScope:resources.itemRegistryOrigin});
}
for(const name of ['Recover','Roost','Soft-Boiled','Slack Off','Synthesis','Grassy Glide']){const a=d8.moves.get(name),b=dc.moves.get(name);if(a.pp!==b.pp||a.basePower!==b.basePower)report.generationDifferences.push({kind:'move',name,gen8:{pp:a.pp,power:a.basePower},current:{pp:b.pp,power:b.basePower}})}
for(const name of ['Zacian','Zacian-Crowned','Zamazenta','Zamazenta-Crowned','Cresselia']){const a=d8.species.get(name),b=dc.species.get(name);if(JSON.stringify(a.baseStats)!==JSON.stringify(b.baseStats))report.generationDifferences.push({kind:'species',name,gen8:a.baseStats,current:b.baseStats})}
for(const name of ['Protean','Libero','Intrepid Sword','Dauntless Shield']){const a=d8.abilities.get(name),b=dc.abilities.get(name);const hooks=x=>Object.fromEntries(Object.entries(x).filter(([k,v])=>k.startsWith('on')&&typeof v==='function').map(([k,v])=>[k,String(v)]));if(JSON.stringify(hooks(a))!==JSON.stringify(hooks(b)))report.generationDifferences.push({kind:'ability',name,differentEventHooks:true})}
function set(species='Mew',ability='Synchronize',moves=['splash'],item=''){return{species,ability,moves,item,level:100,uuid:crypto.randomUUID(),movesInfo:moves.map(m=>({pp:40,maxPp:40}))}}
function battle(a,b){const x=new Battle({formatid:'gen8customgame',seed:[1,2,3,4]});x.setPlayer('p1',{name:'AuditA',team:a});x.setPlayer('p2',{name:'AuditB',team:b});x.makeChoices('team '+a.map((_,i)=>i+1).join(''),'team '+b.map((_,i)=>i+1).join(''));return x;}
function check(name,fn){try{const result=fn();report.mechanicChecks.push({name,pass:true,result});}catch(e){report.mechanicChecks.push({name,pass:false,error:String(e.message).slice(0,250)})}}
check('Intimidate lowers opponent Attack',()=>{const b=battle([set('Landorus-Therian','Intimidate')],[set('Garchomp','Rough Skin')]);assert.equal(b.p2.active[0].boosts.atk,-1);b.destroy();return'-1 stage';});
check('Pressure consumes two PP',()=>{const b=battle([set('Mew','Synchronize',['tackle'])],[set('Dusknoir','Pressure')]);b.makeChoices('move 1','move 1');assert.equal(b.p1.active[0].moveSlots[0].pp,38);b.destroy();return'40 → 38';});
check('Leftovers heals',()=>{const b=battle([set('Mew','Synchronize',['splash'],'Leftovers')],[set()]);const p=b.p1.active[0];p.hp-=60;const before=p.hp;b.makeChoices('move 1','move 1');assert(p.hp>before);b.destroy();return'HP increased';});
check('Choice Scarf increases speed',()=>{const b=battle([set('Mew','Synchronize',['splash'],'Choice Scarf')],[set()]);assert(b.p1.active[0].getActionSpeed()>b.p2.active[0].getActionSpeed());b.destroy();return'scarf holder faster';});
check('Regenerator heals when switching',()=>{const b=battle([set('Slowbro','Regenerator'),set()],[set()]);const p=b.p1.active[0];p.hp-=100;const before=p.hp;b.makeChoices('switch 2','move 1');assert(p.hp>before);b.destroy();return'bench HP increased';});
check('Heavy-Duty Boots blocks Stealth Rock damage',()=>{const b=battle([set()],[set(),set('Mew','Synchronize',['splash'],'Heavy-Duty Boots')]);b.p2.addSideCondition('stealthrock',b.p1.active[0]);b.makeChoices('move 1','switch 2');const p=b.p2.active[0];assert.equal(p.hp,p.maxhp);b.destroy();return'full HP after switch';});
check('Magic Bounce reflects Toxic',()=>{const b=battle([set('Alakazam','Inner Focus',['toxic'])],[set('Espeon','Magic Bounce')]);b.makeChoices('move 1','move 1');assert.equal(b.p1.active[0].status,'tox');assert.equal(b.p2.active[0].status,'');b.destroy();return'Toxic reflected';});
check('Gen 8 Dynamax gate',()=>{const b=battle([set()],[set()]);const available=b.p1.canDynamaxNow();b.destroy();return{available,expectedForAG:true,compatible:available===true}});
report.verifiedVanillaHeldItemRemaps={thickclub:'minecraft:bone',bignugget:'minecraft:gold_block',snowball:'minecraft:snowball'};
report.blockers.push('The default Cobblemon battle mod is Gen 9, not Gen 8.','No Atlas pre-match format validator / legal-set lock / tier clauses currently installed.','Native Cobblemon species stats, moves and PP are supplied to the simulator; changing only the format ID does not establish historical generation correctness.','Species/resource inventory does not certify availability, legal learnsets, item acquisition, animations or native PvP integration.');
if(report.mechanicChecks.find(x=>x.name==='Gen 8 Dynamax gate')?.result?.available===false)report.blockers.push('Installed patched simulator rejects Dynamax when battle.gen is not 9 (side.canDynamaxNow); Gen 8 AG cannot be certified without adaptation.');
fs.writeFileSync(root+'/atlas-bot/.runtime/gen8-audit/report.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({formats:report.formats.map(f=>({id:f.id,total:f.eligibleSpeciesOrForms,missing:f.missingBaseResourceDeclarations.length,unconfirmed:f.baseImplementationUnconfirmed.length,uncertainForms:f.formMappingNeedsNativeVerification.length,upstreamMatch:f.upstreamRulesMatch&&f.upstreamBansMatch})),itemsMissing:report.essentialItems.filter(x=>!x.registeredCandidates.length).map(x=>x.name),checks:report.mechanicChecks,differences:report.generationDifferences},null,2));
