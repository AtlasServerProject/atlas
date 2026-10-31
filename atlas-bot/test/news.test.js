import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Collection, ChannelType, PermissionFlagsBits } from 'discord.js';
import { createNews, newsMessage, validateFeed, fetchNews, fileNewsStore } from '../src/news.js';
import { prepareNewsChannel } from '../src/news-channel.js';
import { config } from '../src/config.js';
import { createHandler } from '../src/commands.js';

const note = { id: 'kits', version: '1.30.3', category: 'Gameplay', dateLabel: '04 out. 2026',
  title: 'Novos comandos', summary: 'Kits por nível.', changes: ['Atalhos antigos continuam funcionando.'], notice: 'Em testes.' };
const settings = { guildId: 'g', newsChannelId: 'c', newsFeedUrl: 'https://atlascobblemon.com.br/updates.json' };
function fixture() {
  let state = { version: 1, channels: {} };
  let feed = { schemaVersion: 1, notes: [structuredClone(note)] };
  const messages = new Collection();
  const sent = [];
  const edits = [];
  const channel = { id: 'c', guildId: 'g', isTextBased: () => true,
    messages: { fetch: async value => {
      if (typeof value === 'object') return messages;
      if (!messages.has(value)) throw new Error('Message missing');
      return messages.get(value);
    } },
    send: async payload => {
      sent.push(payload);
      const message = { id: String(sent.length), author: { id: 'bot' }, embeds: payload.embeds,
        edit: async update => { edits.push(update); message.embeds = update.embeds; return message; } };
      messages.set(message.id, message);
      return message;
    },
  };
  const client = { user: { id: 'bot' }, channels: { fetch: async () => channel } };
  const dependencies = { load: async () => feed, store: {
    read: async () => structuredClone(state), write: async value => { state = structuredClone(value); },
  } };
  return { sent, edits, channel, client, dependencies,
    setFeed: value => { feed = value; }, state: () => state,
    news: createNews(client, { ...settings }, dependencies) };
}

test('message preserves validation limits and disables all mentions', () => {
  const payload = newsMessage({ ...note, title: '@everyone kits' }, settings.newsFeedUrl);
  assert.deepEqual(payload.allowedMentions, { parse: [] });
  assert.equal(payload.embeds[0].url, 'https://atlascobblemon.com.br/notices#kits');
  assert.ok(payload.embeds[0].fields.some(field => field.value === note.notice));
  assert.ok(payload.embeds[0].description.length < 4096);
});

test('invalid feeds, duplicates and oversized responses are rejected', async () => {
  assert.throws(() => validateFeed({ schemaVersion: 1, notes: [{ ...note, id: undefined }] }));
  assert.throws(() => validateFeed({ schemaVersion: 1, notes: [note, note] }));
  assert.throws(() => validateFeed({ schemaVersion: 2, notes: [] }));
  await assert.rejects(fetchNews(settings.newsFeedUrl, async () => new Response('x'.repeat(300000))));
  const result = await fetchNews(settings.newsFeedUrl, async () => new Response(JSON.stringify({ schemaVersion: 1, notes: [note] })));
  assert.equal(result.notes.length, 1);
});

test('preview does not publish; confirmation and restart do not duplicate', async () => {
  const f = fixture();
  await f.news.preview();
  assert.equal(f.sent.length, 0);
  await f.news.publish();
  await createNews(f.client, settings, f.dependencies).publish();
  assert.equal(f.sent.length, 1);
  assert.equal(f.sent[0].enforceNonce, true);
});

test('initial sync records historical notes; new notes publish once and corrections edit', async () => {
  const f = fixture();
  assert.equal(await f.news.sync(), 0);
  assert.equal(f.sent.length, 0);
  const latest = { ...note, id: 'new-version', version: '1.30.4' };
  f.setFeed({ schemaVersion: 1, notes: [latest, note] });
  assert.equal(await f.news.sync(), 1);
  assert.equal(await f.news.sync(), 0);
  assert.equal(f.sent.length, 1);
  f.setFeed({ schemaVersion: 1, notes: [{ ...latest, summary: 'Correção nas instruções.' }, note] });
  assert.equal(await f.news.sync(), 1);
  assert.equal(f.sent.length, 1);
  assert.equal(f.edits.length, 1);
});

test('concurrent publication requests share one serialized journal', async () => {
  const f = fixture();
  await Promise.all([f.news.publish(), f.news.publish(), f.news.sync()]);
  assert.equal(f.sent.length, 1);
});

test('uncertain delivery is recovered from bot message instead of resending', async () => {
  const f = fixture();
  const send = f.channel.send;
  f.channel.send = async payload => { await send(payload); throw new Error('Network interrupted after acceptance'); };
  await assert.rejects(f.news.publish());
  f.channel.send = send;
  await f.news.publish();
  assert.equal(f.sent.length, 1);
  assert.equal(f.edits.length, 1);
  assert.equal(f.state().channels['g:c'].entries.kits.pending, false);
});

test('uncertain delivery without a matching message stops automatic retries', async () => {
  const f = fixture();
  f.channel.send = async () => { throw new Error('Network failure'); };
  await assert.rejects(f.news.publish());
  await assert.rejects(f.news.publish(), /Envio anterior sem confirmação/);
});

test('wrong server and corrupt state never trigger a publication', async t => {
  const f = fixture();
  f.channel.guildId = 'other';
  await assert.rejects(f.news.publish());
  assert.equal(f.sent.length, 0);
  const dir = await mkdtemp(join(tmpdir(), 'atlas-news-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const path = join(dir, 'state.json');
  const store = fileNewsStore(path);
  await store.write({ version: 1, channels: {} });
  assert.deepEqual(await store.read(), { version: 1, channels: {} });
  await writeFile(path, '{bad json');
  await assert.rejects(store.read());
});

test('configuration keeps automatic publishing off and validates explicit enablement', () => {
  const env = { DISCORD_TOKEN: 'test', DISCORD_APPLICATION_ID: '123456789012345678', DISCORD_GUILD_ID: '234567890123456789' };
  assert.equal(config(env).newsAuto, false);
  assert.throws(() => config({ ...env, ATLAS_NEWS_AUTO: 'true' }));
  assert.throws(() => config({ ...env, ATLAS_NEWS_FEED_URL: 'http://example.com/updates.json' }));
  assert.throws(() => config({ ...env, ATLAS_NEWS_INTERVAL_SECONDS: '5' }));
});

test('only owner in private channel can prepare or publish news', async () => {
  let denied = 0;
  const handler = createHandler({}, { guildId: 'g', ownerId: 'owner', ownerChannelId: 'private' });
  for (const commandName of ['preparar-novidades', 'publicar-novidade', 'boas-vindas']) {
    await handler({ isChatInputCommand: () => true, commandName, guildId: 'g', user: { id: 'other' }, channelId: 'private',
      reply: async () => denied++ });
  }
  assert.equal(denied, 3);
});

test('channel setup creates only news, uses read-only permissions and reuses existing channel', async () => {
  const channels = new Collection();
  channels.set('group', { id: 'group', type: ChannelType.GuildCategory, name: '📌 ATLAS • INFORMAÇÕES' });
  const writes = [];
  const guild = { id: 'g', members: { me: { id: 'bot' } }, channels: {
    cache: channels, fetch: async () => channels,
    create: async data => {
      writes.push(data);
      const result = { ...data, id: 'news', edit: async () => {}, permissionOverwrites: { edit: async () => {} } };
      channels.set(result.id, result);
      return result;
    },
  } };
  const channel = await prepareNewsChannel(guild);
  assert.equal(channel.name, '📰・novidades');
  assert.equal(writes.length, 1);
  assert.ok(writes[0].permissionOverwrites[0].deny.includes(PermissionFlagsBits.SendMessages));
  assert.equal((await prepareNewsChannel(guild)).id, channel.id);
  assert.equal(writes.length, 1);
});
