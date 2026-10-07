import test from 'node:test';
import assert from 'node:assert/strict';
import {createMinecraftStatus,statusText} from '../src/minecraft-status.js';
test('cache evita consultas concorrentes; falha não conserva contagem antiga',async()=>{
 let calls=0;let time=100000;let fail=false;
 const monitor=createMinecraftStatus({},async()=>{calls++;if(fail)throw Error();return{players:{online:3,max:50}}},()=>time);
 const [a,b]=await Promise.all([monitor.read(),monitor.read()]);
 assert.equal(calls,1);assert.equal(a.online,3);assert.deepEqual(a,b);
 await monitor.read();assert.equal(calls,1);
 time+=11000;fail=true;const down=await monitor.read();
 assert.equal(down.available,false);assert.equal(down.online,undefined);assert.match(statusText(down),/indisponível/);
 time+=11000;fail=false;assert.equal((await monitor.read()).available,true);
});
test('zero é online e contagem inválida é indisponível',async()=>{
 const good=createMinecraftStatus({},async()=>({players:{online:0,max:50}}));
 assert.match(statusText(await good.read()),/0\/50/);
 const bad=createMinecraftStatus({},async()=>({players:{online:-1,max:50}}));
 assert.equal((await bad.read()).available,false);
});
