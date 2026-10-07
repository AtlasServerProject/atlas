import test from 'node:test';
import assert from 'node:assert/strict';
import { Collection, ChannelType, PermissionFlagsBits } from 'discord.js';
import { welcomeMember, resolveWelcomeChannel, diagnoseWelcome, repairWelcomePermissions } from '../src/welcome.js';
import { config } from '../src/config.js';

test('entrada menciona apenas o novo membro e envia guia no canal configurado', async () => {
  const sent = [];
  const channel = { id: 'welcome', name: '👋・boas-vindas', guildId: 'atlas', type: ChannelType.GuildText,
    permissionsFor: () => ({ has: () => true }), send: async data => sent.push(data) };
  const member = { id: 'new-member', user: { bot: false, displayAvatarURL: () => 'https://cdn.discordapp.com/embed/avatars/0.png' },
    guild: { id: 'atlas', members: { me: { id: 'bot' } }, channels: { fetch: async () => channel, cache: new Collection([['welcome', channel], ['rules', { id: 'rules', name: '📜・regras' }]]) } } };
  const settings = { guildId: 'atlas', welcomeChannelId: 'welcome' };
  await welcomeMember(member, settings);
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0].allowedMentions, { parse: [], users: ['new-member'] });
  assert.match(sent[0].embeds[0].toJSON().description, /<#rules>/);
  member.user.bot = true;
  await welcomeMember(member, settings);
  member.user.bot = false;
  await welcomeMember(member, { ...settings, guildId: 'other' });
  await welcomeMember(member, { ...settings, welcomeEnabled: false });
  assert.equal(sent.length, 1);
  channel.guildId = 'other';
  await assert.rejects(welcomeMember(member, settings));
});

function fixture() {
  const sent = [];
  const channel = { id: 'welcome', name: '👋・bem-vindo', guildId: 'atlas', type: ChannelType.GuildText,
    permissionsFor: () => ({ has: () => true }), send: async payload => sent.push(payload) };
  const cache = new Collection([['welcome', channel]]);
  const guild = { id: 'atlas', members: { me: { id: 'bot' } },
    channels: { cache, fetch: async id => id ? cache.get(id) : cache } };
  const member = { id: 'member', user: { bot: false, displayAvatarURL: () => 'https://cdn.discordapp.com/embed/avatars/0.png' }, guild };
  return { sent, channel, guild, member, settings: { guildId: 'atlas', welcomeEnabled: true } };
}

test('missing channel ID discovers bem-vindo and still sends welcome', async () => {
  const f = fixture();
  await welcomeMember(f.member, f.settings);
  assert.equal(f.sent.length, 1);
  assert.equal(f.sent[0].embeds[0].toJSON().color, 0x78ddff);
});

test('ambiguous channel names require explicit ID and never send to an arbitrary channel', async () => {
  const f = fixture();
  f.guild.channels.cache.set('second', { ...f.channel, id: 'second', name: 'boas-vindas' });
  await assert.rejects(welcomeMember(f.member, f.settings), /mais de um canal/);
  assert.equal(f.sent.length, 0);
  assert.equal((await resolveWelcomeChannel(f.guild, { ...f.settings, welcomeChannelId: 'welcome' })).id, 'welcome');
});

test('invalid explicit ID does not silently fall back to a channel by name', async () => {
  const f = fixture();
  await assert.rejects(welcomeMember(f.member, { ...f.settings, welcomeChannelId: 'missing' }), /inválido/);
  assert.equal(f.sent.length, 0);
});

test('missing EmbedLinks reports actionable error before trying to send', async () => {
  const f = fixture();
  f.channel.permissionsFor = () => ({ has: flag => flag !== PermissionFlagsBits.EmbedLinks });
  await assert.rejects(welcomeMember(f.member, f.settings), /Inserir links/);
  assert.equal(f.sent.length, 0);
  const report = await diagnoseWelcome(f.guild, f.settings, false);
  assert.match(report, /Server Members Intent/);
  assert.match(report, /Inserir links/);
});

test('diagnostic verifies destination without sending or re-welcoming existing members', async () => {
  const f = fixture();
  const report = await diagnoseWelcome(f.guild, f.settings, true);
  assert.match(report, /<#welcome>/);
  assert.match(report, /Permissões de envio e imagem: OK/);
  assert.equal(f.sent.length, 0);
});

test('repair grants only the bot the permissions needed for welcome embeds', async () => {
  const f = fixture();
  const writes = [];
  f.channel.permissionOverwrites = { edit: async (...args) => writes.push(args) };
  await repairWelcomePermissions(f.guild, f.settings);
  assert.equal(writes.length, 1);
  assert.equal(writes[0][0], 'bot');
  assert.deepEqual(writes[0][1], { ViewChannel: true, SendMessages: true, EmbedLinks: true });
  assert.equal(f.sent.length, 0);
});

test('Discord send failures preserve safe error codes rather than a generic failure', async () => {
  const f = fixture();
  f.channel.send = async () => { throw Object.assign(new Error('private request detail'), { code: 50013 }); };
  await assert.rejects(welcomeMember(f.member, f.settings), error => error.message.includes('50013') && !error.message.includes('private'));
});

test('welcome defaults on independently of channel ID and can be explicitly disabled', () => {
  const env = { DISCORD_TOKEN: 'test', DISCORD_APPLICATION_ID: '123456789012345678', DISCORD_GUILD_ID: '234567890123456789' };
  assert.equal(config(env).welcomeEnabled, true);
  assert.equal(config({ ...env, DISCORD_WELCOME_ENABLED: 'false' }).welcomeEnabled, false);
  assert.throws(() => config({ ...env, DISCORD_WELCOME_ENABLED: 'typo' }));
});
