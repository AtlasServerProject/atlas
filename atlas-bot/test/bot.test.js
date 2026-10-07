import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { Collection, ChannelType, PermissionFlagsBits } from 'discord.js';
import { config } from '../src/config.js';
import { authorized, eventMessage, createBridge } from '../src/bridge.js';
import { createHandler, publish } from '../src/commands.js';
import { applyStructure } from '../src/structure.js';
import { isOwnerContext, administer } from '../src/admin.js';

const env = { DISCORD_TOKEN: 'test-only', DISCORD_APPLICATION_ID: '123456789012345678', DISCORD_GUILD_ID: '234567890123456789' };
test('configuração exige IDs, segredo forte e canal para integração', () => {
  assert.equal(config(env).bridgeSecret, '');
  assert.throws(() => config({ ...env, DISCORD_GUILD_ID: 'invalid' }));
  assert.throws(() => config({ ...env, ATLAS_BRIDGE_SECRET: 'short' }));
  assert.throws(() => config({ ...env, ATLAS_BRIDGE_SECRET: 'a'.repeat(32) }));
  assert.throws(() => config({ ...env, MODPACK_URL: 'http://example.com' }));
});
test('eventos exigem autenticação e formato conhecido', () => {
  assert.equal(authorized('Bearer abc', 'abc'), true);
  assert.equal(authorized('Bearer abd', 'abc'), false);
  assert.equal(authorized('', ''), false);
  assert.throws(() => eventMessage({ type: 'constructor', message: 'x' }));
  assert.throws(() => eventMessage({ type: 'started', message: 'x'.repeat(1501) }));
  assert.match(eventMessage({ type: 'started', message: 'Pronto!' }), /Pronto!/);
});
test('endpoint rejeita requisições inválidas e publica evento autenticado', async t => {
  const sent = [];
  const server = createBridge('a'.repeat(32), async message => sent.push(message));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => { server.closeAllConnections(); server.close(); });
  const url = `http://127.0.0.1:${server.address().port}/events`;
  const headers = { Authorization: `Bearer ${'a'.repeat(32)}`, 'Content-Type': 'application/json' };
  assert.equal((await fetch(url, { method: 'POST' })).status, 401);
  assert.equal((await fetch(url, { method: 'POST', headers, body: '{}' })).status, 400);
  assert.equal((await fetch(url, { method: 'POST', headers, body: 'x'.repeat(9000) })).status, 413);
  assert.equal((await fetch(url, { method: 'POST', headers, body: JSON.stringify({ type: 'started', message: 'Pokémon disponível' }) })).status, 202);
  assert.equal(sent.length, 1);
  assert.match(sent[0], /Pokémon/);
  assert.equal((await fetch(url, { method: 'POST', headers, body: '{}' })).status, 429);
});
test('admin e servidor são verificados antes de executar comandos', async () => {
  const replies = [];
  const handler = createHandler({}, { guildId: env.DISCORD_GUILD_ID });
  const base = { isChatInputCommand: () => true, commandName: 'estrutura', reply: async data => replies.push(data.content) };
  await handler({ ...base, guildId: 'other' });
  await handler({ ...base, guildId: env.DISCORD_GUILD_ID, memberPermissions: { has: () => false } });
  assert.match(replies[0], /somente/);
  assert.match(replies[1], /DONO/);
});
test('administração exige conta e canal exatos, mesmo para outros administradores', () => {
  const settings = { guildId: 'g', ownerId: 'owner', ownerChannelId: 'private' };
  const interaction = { guildId: 'g', user: { id: 'owner' }, channelId: 'private' };
  assert.equal(isOwnerContext(interaction, settings), true);
  assert.equal(isOwnerContext({ ...interaction, user: { id: 'admin' } }, settings), false);
  assert.equal(isOwnerContext({ ...interaction, channelId: 'public' }, settings), false);
  assert.equal(isOwnerContext(interaction, { guildId: 'g' }), false);
});
test('permissões preservam bits não relacionados e protegem o canal do dono', async () => {
  let written;
  let targetChannel = null;
  const role = { id: 'role', name: 'Equipe', editable: true, managed: false,
    permissions: { bitfield: PermissionFlagsBits.ViewChannel }, setPermissions: async bits => { written = bits; } };
  const interaction = { user: { id: 'owner' }, channel: { parentId: 'private-category' },
    guild: { roles: { fetch: async () => role } }, options: {
      getSubcommand: () => 'permissao', getRole: () => role, getChannel: () => targetChannel,
      getString: () => 'SendMessages', getBoolean: () => true,
    } };
  await administer(interaction, { ownerChannelId: 'private' });
  assert.equal(written, PermissionFlagsBits.ViewChannel | PermissionFlagsBits.SendMessages);
  written = undefined;
  targetChannel = { id: 'private' };
  assert.match(await administer(interaction, { ownerChannelId: 'private' }), /diretamente no Discord/);
  assert.equal(written, undefined);
});
test('publicação impede menções e rejeita canal de outro servidor', async () => {
  let sent;
  const settings = { guildId: 'atlas', channelId: 'channel' };
  const channel = { guildId: 'atlas', isTextBased: () => true, send: async body => { sent = body; } };
  const client = { channels: { fetch: async () => channel } };
  await publish(client, settings, '@everyone teste');
  assert.deepEqual(sent.allowedMentions, { parse: [] });
  channel.guildId = 'other';
  await assert.rejects(publish(client, settings, 'test'));
});
test('estrutura é retomável, preserva existentes e não duplica', async () => {
  let next = 0;
  const channels = new Collection();
  channels.set('existing', { id: 'existing', name: 'outro-canal', type: ChannelType.GuildText, parentId: null });
  const roles = new Collection();
  const guild = { id: 'guild', members: { me: { id: 'bot' } },
    channels: { cache: channels, fetch: async () => channels, create: async data => {
      const value = { ...data, id: String(++next), parentId: data.parent };
      channels.set(value.id, value); return value;
    } },
    roles: { cache: roles, fetch: async () => roles, create: async data => {
      assert.deepEqual(data.permissions, []);
      roles.set(String(++next), data); return data;
    } },
  };
  await applyStructure(guild);
  const size = channels.size;
  assert.equal(size, 17);
  assert.equal(roles.size, 2);
  assert.equal(await applyStructure(guild), 'A estrutura já existe.');
  assert.equal(channels.size, size);
  assert.equal(channels.get('existing').parentId, null);
});
