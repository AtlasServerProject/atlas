import { createHash } from 'node:crypto';
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const text = (value, max) => typeof value === 'string' && value.trim().length > 0 && value.length <= max;

export function validateFeed(feed) {
  if (feed?.schemaVersion !== 1 || !Array.isArray(feed.notes) || feed.notes.length > 100) throw new Error('Feed de novidades inválido.');
  const ids = new Set();
  for (const note of feed.notes) {
    if (typeof note?.id !== 'string' || !/^[a-z0-9-]{1,60}$/.test(note.id) || note.id === 'constructor' || ids.has(note.id)
      || !text(note.title, 256) || !text(note.summary, 1024)
      || !text(note.version, 100) || !text(note.category, 100) || !text(note.dateLabel, 100)
      || !Array.isArray(note.changes) || !note.changes.length || note.changes.length > 20
      || !note.changes.every(change => text(change, 1000))
      || (note.notice !== undefined && !text(note.notice, 1500))) throw new Error('Nota de atualização inválida.');
    ids.add(note.id);
  }
  return feed;
}

export async function fetchNews(url, fetcher = fetch) {
  const response = await fetcher(url, { signal: AbortSignal.timeout(10000), redirect: 'error', cache: 'no-store' });
  if (!response.ok) throw new Error('Não foi possível consultar as novidades do site.');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 256 * 1024) throw new Error('Feed de novidades excedeu o limite.');
      chunks.push(Buffer.from(value));
    }
    return validateFeed(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  } finally { await reader.cancel(); }
}

export function newsMessage(note, feedUrl) {
  const url = new URL('/notices', feedUrl);
  url.hash = note.id;
  const bullets = note.changes.slice(0, 4).map(change => `• ${change}`).join('\n');
  const details = bullets.length > 2400 ? bullets.slice(0, 2397) + '…' : bullets;
  return {
    allowedMentions: { parse: [] },
    embeds: [{
      color: 0x78ddff,
      title: note.title,
      url: url.href,
      description: `${note.summary}\n\n${details}`,
      fields: [
        { name: 'Versão', value: note.version, inline: true },
        { name: 'Categoria', value: note.category, inline: true },
        { name: 'Registro', value: note.dateLabel, inline: true },
        ...(note.notice ? [{ name: 'Estado e validação', value: note.notice.slice(0, 1024) }] : []),
        { name: 'Leia a nota completa', value: `[Novidades no site Atlas](${url.href})` },
      ],
      footer: { text: `Atlas • novidade:${note.id}` },
    }],
  };
}

export function fileNewsStore(path) {
  return {
    async read() {
      try {
        const value = JSON.parse(await readFile(path, 'utf8'));
        if (value.version !== 1 || !value.channels || typeof value.channels !== 'object' || Array.isArray(value.channels)) throw new Error('Estado das novidades inválido.');
        return value;
      } catch (error) {
        if (error.code === 'ENOENT') return { version: 1, channels: {} };
        throw error; // Never reset a corrupt journal and republish old messages.
      }
    },
    async write(value) {
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path + '.tmp', JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
      await rename(path + '.tmp', path);
    },
  };
}

export function createNews(client, settings, dependencies = {}) {
  const load = dependencies.load || (() => fetchNews(settings.newsFeedUrl));
  const store = dependencies.store || fileNewsStore(settings.newsStateFile);
  let flight = Promise.resolve();
  const exclusive = action => {
    const result = flight.then(action);
    flight = result.catch(() => {});
    return result;
  };
  async function feed() {
    if (!settings.newsFeedUrl) throw new Error('Novidades do site ainda não configuradas.');
    return validateFeed(await load());
  }
  async function channel() {
    if (!settings.newsChannelId) throw new Error('Canal de novidades ainda não configurado.');
    const target = await client.channels.fetch(settings.newsChannelId);
    if (!target || target.guildId !== settings.guildId || !target.isTextBased() || !target.send || target.isThread?.()) throw new Error('Canal de novidades inválido.');
    return target;
  }
  function journal(state) {
    const key = `${settings.guildId}:${settings.newsChannelId}`;
    return state.channels[key] ||= { initialized: false, entries: {} };
  }
  async function publishNote(target, note, state, history) {
    const hash = digest(note);
    let entry = history.entries[note.id];
    if (entry?.pending) {
      // A crash or network error may have happened after Discord accepted the send.
      // Recover by marker; never blindly send a second announcement.
      const recent = await target.messages.fetch({ limit: 100 });
      const found = recent.find(message => message.author?.id === client.user.id
        && message.embeds?.some(embed => embed.footer?.text === `Atlas • novidade:${note.id}`));
      if (!found) throw new Error('Envio anterior sem confirmação. Confira o canal e o estado local antes de tentar novamente.');
      entry.messageId = found.id;
      entry.pending = false;
      entry.hash = ''; // Reconcile the recovered message against the current content.
      await store.write(state);
    }
    if (entry?.messageId && entry.hash === hash) return false;
    const payload = newsMessage(note, settings.newsFeedUrl);
    if (entry?.messageId) {
      const existing = await target.messages.fetch(entry.messageId);
      if (existing.author.id !== client.user.id) throw new Error('Mensagem de novidade não pertence ao bot.');
      await existing.edit(payload);
    } else {
      history.entries[note.id] = { hash: entry?.hash || '', pending: true, messageId: null };
      await store.write(state); // Persist intent before any external send.
      const message = await target.send({ ...payload,
        nonce: digest(`${settings.newsChannelId}:${note.id}`).slice(0, 24), enforceNonce: true });
      entry = history.entries[note.id];
      entry.messageId = message.id;
    }
    history.entries[note.id] = { hash, messageId: entry.messageId, pending: false };
    await store.write(state);
    return true;
  }
  return {
    async preview(id) {
      const notes = (await feed()).notes;
      const note = id ? notes.find(item => item.id === id) : notes[0];
      if (!note) throw new Error('Novidade não encontrada.');
      return { id: note.id, payload: newsMessage(note, settings.newsFeedUrl) };
    },
    publish(id) {
      return exclusive(async () => {
        const notes = (await feed()).notes;
        const note = id ? notes.find(item => item.id === id) : notes[0];
        if (!note) throw new Error('Novidade não encontrada.');
        const target = await channel();
        const state = await store.read();
        const history = journal(state);
        return await publishNote(target, note, state, history) ? 'Novidade publicada ou atualizada.' : 'Esta novidade já está publicada e atualizada.';
      });
    },
    sync() {
      return exclusive(async () => {
        const notes = (await feed()).notes;
        const target = await channel();
        const state = await store.read();
        const history = journal(state);
        if (!history.initialized) {
          for (const note of notes) history.entries[note.id] ||= { hash: digest(note), messageId: null, pending: false };
          history.initialized = true;
          await store.write(state);
          return 0; // First activation records the baseline without flooding the channel.
        }
        let sent = 0;
        for (const note of [...notes].reverse()) {
          const entry = history.entries[note.id];
          if (entry?.hash === digest(note) && !entry.pending) continue;
          if (await publishNote(target, note, state, history)) sent++;
        }
        return sent;
      });
    },
  };
}

export function startNews(news, settings) {
  if (!settings.newsAuto) return () => {};
  let busy = false;
  let stopped = false;
  const tick = async () => {
    if (busy || stopped) return;
    busy = true;
    try { await news.sync(); }
    catch { console.error('Novidades: falha de sincronização. Verifique feed, canal, permissões e estado persistente.'); }
    finally { busy = false; }
  };
  const timer = setInterval(tick, settings.newsInterval * 1000);
  timer.unref?.();
  void tick();
  return () => { stopped = true; clearInterval(timer); };
}
