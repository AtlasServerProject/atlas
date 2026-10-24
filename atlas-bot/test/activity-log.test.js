import test from 'node:test';
import assert from 'node:assert/strict';
import { redact } from '../src/activity-log.js';
test('redacts passwords, linking codes, webhook credentials and bot tokens', () => {
 for (const text of ['/login test-password', '/register secret secret', '/site vincular 123456', 'senha=private', 'token: private', 'https://discord.com/api/webhooks/123456/very-secret']) {
  const clean=redact(text); assert(!clean.includes('test-password')); assert(!clean.includes('123456')); assert(!clean.includes('private')); assert(!clean.includes('very-secret'));
 }
});
test('preserves ordinary chat for staff review', () => { assert.equal(redact('Olá, preciso de ajuda no GTS.'), 'Olá, preciso de ajuda no GTS.'); });
import { EventEmitter } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { Events } from 'discord.js';
import { startActivityLog, DISCORD_LOG_CHANNEL } from '../src/activity-log.js';
test('durable snapshots redact secrets, preserve edits/deletes and avoid log loops', () => {
 const original=process.cwd(), dir=mkdtempSync(join(tmpdir(),'atlas-log-')); process.chdir(dir);
 const client=new EventEmitter();client.user={id:'bot'};client.isReady=()=>false;
 const stop=startActivityLog(client,{guildId:'guild'});
 try {
  const event=(t,d)=>client.emit(Events.Raw,{t,d:{guild_id:'guild',channel_id:'chat',...d}});
  event('MESSAGE_CREATE',{id:'1',author:{id:'player',username:'Player'},content:'/login private-password'});
  event('MESSAGE_UPDATE',{id:'1',content:'Mensagem editada'});
  event('MESSAGE_DELETE',{id:'1'});
  event('MESSAGE_CREATE',{id:'2',channel_id:DISCORD_LOG_CHANNEL,author:{id:'player'},content:'ignored'});
  const db=new DatabaseSync('.runtime/discord-activity.sqlite');
  const rows=db.prepare('SELECT payload FROM outbox').all();assert.equal(rows.length,3);
  assert(!JSON.stringify(rows).includes('private-password'));
  assert(JSON.stringify(rows.at(-1)).includes('Mensagem editada'));
  assert.equal(db.prepare('SELECT count(*) n FROM snapshots').get().n,0);db.close();
 } finally {stop();process.chdir(original);rmSync(dir,{recursive:true,force:true});}
});
