import test from 'node:test';
import assert from 'node:assert/strict';
import { Collection, ChannelType } from 'discord.js';
import { welcomeMember } from '../src/welcome.js';

test('entrada menciona apenas o novo membro e envia guia no canal configurado', async () => {
  const sent = [];
  const channel = { guildId: 'atlas', type: ChannelType.GuildText, send: async data => sent.push(data) };
  const member = { id: 'new-member', user: { bot: false, displayAvatarURL: () => 'https://cdn.discordapp.com/embed/avatars/0.png' },
    guild: { id: 'atlas', channels: { fetch: async () => channel, cache: new Collection([['rules', { id: 'rules', name: '📜・regras' }]]) } } };
  const settings = { guildId: 'atlas', welcomeChannelId: 'welcome' };
  await welcomeMember(member, settings);
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0].allowedMentions, { parse: [], users: ['new-member'] });
  assert.match(sent[0].embeds[0].toJSON().description, /<#rules>/);
  member.user.bot = true;
  await welcomeMember(member, settings);
  member.user.bot = false;
  await welcomeMember(member, { ...settings, guildId: 'other' });
  await welcomeMember(member, { ...settings, welcomeChannelId: undefined });
  assert.equal(sent.length, 1);
  channel.guildId = 'other';
  await assert.rejects(welcomeMember(member, settings));
});
