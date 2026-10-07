import test from 'node:test';
import assert from 'node:assert/strict';
import {counterNames} from '../src/status-channels.js';
test('contadores distinguem membros Discord, jogadores e indisponibilidade',()=>{
 assert.deepEqual(counterNames(12,{available:true,online:0,max:50},'play.example.com'),['👥・Discord: 12','🌐・play.example.com','🟢・Online: 0/50']);
 const down=counterNames(12,{available:false},'');
 assert.equal(down[1],null);assert.match(down[2],/indisponível/);
 assert.ok(counterNames(12,{available:false},'x'.repeat(200))[1].length<=100);
});
