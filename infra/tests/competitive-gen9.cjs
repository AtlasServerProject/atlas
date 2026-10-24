'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),crypto=require('node:crypto');
const engine='/opt/atlas/server/fabric/showdown';
const root=path.resolve(__dirname,'../../atlas-core/src/main/resources/atlas-competitive');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json')));
const {load,validate}=require(path.join(root,'validator.cjs'));const api=load(engine,manifest);
const {Battle}=require(path.join(engine,'sim/battle'));
let checks=0;
function mon(species='Pikachu',ability='Static',moves=['Thunderbolt'],item=''){return {species,ability,moves,item,level:100,evs:{hp:4,spa:252,spe:252},uuid:crypto.randomUUID(),movesInfo:moves.map(()=>({pp:40,maxPp:40}))};}
function check(tier,team,valid,contains){const r=validate(api,manifest,tier,[team,[mon()]]);assert.equal(r.reports[0].length===0,valid,JSON.stringify(r.reports[0]));if(contains)assert(r.reports[0].join(' ').toLowerCase().includes(contains.toLowerCase()),JSON.stringify(r));checks++;}
check('OU',[mon()],true);
check('OU',[{...mon(),evs:{},level:50}],true); // advisory is not a legality violation
check('OU',[mon('Miraidon','Hadron Engine',['Thunderbolt'])],false,'banned');
check('UU',[mon('Kingambit','Defiant',['Iron Head'])],false,'banned');
check('OU',[mon(),mon()],false,'Species');
check('MONOTYPE',[mon(),mon('Blastoise','Torrent',['Surf'])],false,'type');
check('MONOTYPE',[mon(),mon('Raichu','Static',['Thunderbolt'])],true);
check('OU',[mon('Amoonguss','Regenerator',['Spore'])],false,'Spore');
check('UBERS',[mon('Amoonguss','Regenerator',['Spore'])],true);
check('OU',[mon('Articuno','Pressure',['Sheer Cold'])],false,'OHKO');
check('OU',[mon('Clefable','Magic Guard',['Minimize'])],false,'Evasion');
check('OU',[mon('Pikachu','Static',['Thunderbolt'],"King's Rock")],false,'banned');
check('OU',[mon('Pikachu','Huge Power',['Thunderbolt'])],false,'Huge Power');
check('OU',[mon('Pikachu','Static',['Draco Meteor'])],false,'learn');
check('OU',[{...mon(),evs:{hp:252,atk:252,def:252}}],false,'EV');
check('OU',[{...mon(),ivs:{hp:32}}],false,'IV');
check('UBERS',[mon('Calyrex-Shadow','As One (Spectrier)',['Astral Barrage'])],false,'banned');
check('AG',[mon('Calyrex-Shadow','As One (Spectrier)',['Astral Barrage'])],true);
check('AG',[mon(),mon()],true);
check('AG',[mon('Smeargle','Moody',['Spore','Baton Pass'])],true);
check('AG',[mon('UnknownAddonSpecies','Pressure',['Tackle'])],false);
// Golden sample using the exact Cobblemon packed layout (UUID/HP/status/PP fields).
const packed=['Pikachu','','00000000-0000-0000-0000-000000000001','200','','0','leftovers','static','thunderbolt','15/15','Timid','4,0,0,252,0,252','M',',,,,,','','100','255,pokeball,,,0,Electric'].join('|');
const decoded=api.Teams.unpack(packed);assert.equal(decoded[0].species,'Pikachu');assert.equal(decoded[0].ability,'Static');assert.equal(validate(api,manifest,'OU',[packed,packed]).ok,true);checks++;
function battle(tier,teams){
 const b=new Battle({format:{mod:'gen9',gameType:'singles',gen:9,ruleset:[manifest.formats[tier],'Dynamax Clause']},seed:[1,2,3,4]});
 b.setPlayer('p1',{name:'A',team:teams[0]});b.setPlayer('p2',{name:'B',team:teams[1]});
 b.makeChoices('team '+teams[0].map((_,i)=>i+1).join(''),'team '+teams[1].map((_,i)=>i+1).join(''));return b;
}
for(const tier of Object.keys(manifest.formats)){
 const b=battle(tier,[[mon()],[mon()]]);assert(b.ruleTable.has('dynamaxclause'));assert.equal(b.p1.canDynamaxNow(),false);checks++;b.destroy();
}
{
 const b=battle('MONOTYPE',[[mon()],[mon()]]);assert.equal(b.p1.active[0].canTerastallize,null);checks++;b.destroy();
}
// Sleep Clause is a battle rule in Ubers: opponent can put only one Pokémon to sleep.
{
 const b=battle('UBERS',[[mon('Amoonguss','Regenerator',['Spore'])],[mon('Pikachu','Static',['Growl']),mon('Raichu','Static',['Growl'])]]);
 b.makeChoices('move 1','move 1');assert.equal(b.p2.active[0].status,'slp');
 b.makeChoices('move 1','switch 2');assert.notEqual(b.p2.active[0].status,'slp');checks++;b.destroy();
}
console.log('CompetitiveGen9 PASS:',checks,'checks: legal/illegal sets, tier bans, species, Monotype, sleep, OHKO, evasion, held item, ability/move legality, EV/IV, AG distinctions, native packed team, Dynamax and runtime Sleep/Terastal clauses');
const corrupted=structuredClone(manifest);corrupted.hashes['config/formats.js']='invalid';assert.throws(()=>load(engine,corrupted),/motor mudou/);console.log('CompetitiveGen9 PASS: mismatched engine snapshot fails closed');
