import { DatabaseSync } from 'node:sqlite';
import { mkdirSync, chmodSync } from 'node:fs';
import { Events } from 'discord.js';
export const DISCORD_LOG_CHANNEL = '1563004705095946251';
const EXCLUDED = new Set([DISCORD_LOG_CHANNEL, '1563004711898980374', '1562967588735295550']);
export function redact(text = '') {
  return String(text).replace(/\b(?:https?:\/\/)?(?:canary\.|ptb\.)?discord(?:app)?\.com\/api(?:\/v\d+)?\/webhooks\/\d+\/[^\s]+/gi, '[WEBHOOK OCULTO]')
    .replace(/\b(?:mfa\.[\w-]+|[\w-]{23,}\.[\w-]{6}\.[\w-]{25,})\b/g, '[TOKEN OCULTO]')
    .replace(/\b(password|senha|token|secret|api[_ -]?key)\s*[:=]\s*[^\s]+/gi, '$1=[OCULTO]')
    .replace(/\/(?:[\w-]+:)?(?:login|register|changepassword|changepass|senha|site\s+vincular)\b[^\n]*/gi, '/[COMANDO SENSÍVEL OCULTO]');
}
export function startActivityLog(client, settings) {
  mkdirSync('.runtime', { recursive: true, mode: 0o700 });
  const db = new DatabaseSync('.runtime/discord-activity.sqlite');
  chmodSync('.runtime/discord-activity.sqlite', 0o600);
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, payload TEXT NOT NULL, seen INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
    PRAGMA user_version=1;`);
  const insert = db.prepare('INSERT INTO outbox(payload) VALUES(?)');
  let stopped = false, busy = false;
  function queue(kind, text) {
    try { insert.run(JSON.stringify({ embeds: [{ title: kind, description: redact(text).slice(0, 3800), timestamp: new Date().toISOString(), color: 7395839 }], allowedMentions: { parse: [] } })); }
    catch { console.error('Logs Discord: armazenamento indisponível; evento não registrado.'); }
  }
  function allowed(d) { return d?.guild_id === settings.guildId && !EXCLUDED.has(d.channel_id); }
  function snapshot(d, previous = {}) {
    return { ...previous, id: d.id, channel_id: d.channel_id, author: d.author || previous.author, content: d.content === undefined ? previous.content : redact(d.content), attachments: d.attachments === undefined ? previous.attachments : d.attachments.map(a => redact(a.filename)), bot: d.author?.bot ?? previous.bot };
  }
  function format(d) { return `Autor: ${d.author?.username || 'desconhecido'} (${d.author?.id || '?'})\nCanal: <#${d.channel_id}>\nMensagem: ${d.id}\n${d.content || '[Sem conteúdo disponível]'}\nAnexos: ${(d.attachments || []).join(', ') || 'nenhum'}`; }
  client.on(Events.Raw, packet => {
    const d = packet.d; if (!allowed(d)) return;
    try {
      if (packet.t === 'MESSAGE_CREATE') {
        if (d.author?.id === client.user?.id) return;
        const value = snapshot(d); db.prepare('INSERT OR REPLACE INTO snapshots VALUES(?,?,?)').run(d.id, JSON.stringify(value), Date.now());
        queue(d.author?.bot ? 'Mensagem de bot' : 'Mensagem enviada', format(value));
      } else if (packet.t === 'MESSAGE_UPDATE') {
        const row = db.prepare('SELECT payload FROM snapshots WHERE id=?').get(d.id); const old = row ? JSON.parse(row.payload) : {};
        if (d.author?.id === client.user?.id || old.author?.id === client.user?.id) return;
        if (d.content === undefined && d.attachments === undefined) return;
        const value = snapshot(d, old);
        if (old.content === value.content && JSON.stringify(old.attachments) === JSON.stringify(value.attachments)) return;
        db.prepare('INSERT OR REPLACE INTO snapshots VALUES(?,?,?)').run(d.id, JSON.stringify(value), Date.now());
        queue('Mensagem editada', `Antes: ${old.content || '[Não registrado]'}\n\nDepois:\n${format(value)}`);
      } else if (packet.t === 'MESSAGE_DELETE' || packet.t === 'MESSAGE_DELETE_BULK') {
        for (const id of d.ids || [d.id]) {
          const row = db.prepare('SELECT payload FROM snapshots WHERE id=?').get(id);
          queue('Mensagem apagada', row ? format(JSON.parse(row.payload)) : `Canal: <#${d.channel_id}>\nMensagem: ${id}\nConteúdo não registrado anteriormente. Autor da exclusão não identificado.`);
          db.prepare('DELETE FROM snapshots WHERE id=?').run(id);
        }
      }
    } catch { console.error('Logs Discord: falha ao registrar evento.'); }
  });
  client.on(Events.InteractionCreate, i => {
    if (i.guildId !== settings.guildId || EXCLUDED.has(i.channelId)) return;
    // Only command names and component type: never arguments, modal answers or custom IDs containing secrets.
    queue('Uso do Atlas Bot', `Usuário: ${i.user.id}\nCanal: <#${i.channelId}>\nAção: ${i.isCommand() ? '/' + i.commandName : 'Componente interativo'}\nID: ${i.id}`);
  });
  client.on(Events.GuildMemberAdd, m => { if (m.guild.id === settings.guildId) queue('Membro entrou', `${m.user.tag} (${m.id})`); });
  client.on(Events.GuildMemberRemove, m => { if (m.guild.id === settings.guildId) queue('Membro saiu', `${m.user.tag} (${m.id})`); });
  client.on(Events.VoiceStateUpdate, (a, b) => { if (b.guild.id === settings.guildId && (a.channelId !== b.channelId || a.serverMute !== b.serverMute || a.serverDeaf !== b.serverDeaf)) queue('Atividade de voz', `Usuário: ${b.id}\nDe: ${a.channelId || 'fora'}\nPara: ${b.channelId || 'fora'}\nMute da equipe: ${b.serverMute}\nSurdez da equipe: ${b.serverDeaf}`); });
  for (const [event, title] of [[Events.ChannelCreate,'Canal criado'],[Events.ChannelDelete,'Canal removido'],[Events.GuildRoleCreate,'Cargo criado'],[Events.GuildRoleDelete,'Cargo removido']]) client.on(event, object => { if (object.guild?.id === settings.guildId) queue(title, `${object.name} (${object.id})`); });
  client.on(Events.ChannelUpdate, (a,b) => { if (b.guild?.id === settings.guildId && !EXCLUDED.has(b.id) && (a.name !== b.name || a.topic !== b.topic)) queue('Canal alterado', `ID: ${b.id}\nNome: ${a.name} → ${b.name}\nDescrição: ${b.topic || 'nenhuma'}`); });
  client.on(Events.GuildRoleUpdate, (a,b) => { if (b.guild.id === settings.guildId) queue('Cargo alterado', `ID: ${b.id}\nNome: ${a.name} → ${b.name}\nPermissões: ${a.permissions.bitfield} → ${b.permissions.bitfield}`); });
  client.on(Events.GuildMemberUpdate, (a,b) => { if (b.guild.id === settings.guildId && (a.nickname !== b.nickname || a.roles.cache.map(r=>r.id).sort().join() !== b.roles.cache.map(r=>r.id).sort().join())) queue('Membro alterado', `Usuário: ${b.id}\nApelido: ${a.nickname || '-'} → ${b.nickname || '-'}\nCargos: ${b.roles.cache.map(r=>r.name).join(', ')}`); });
  client.on(Events.GuildAuditLogEntryCreate, (entry, guild) => {
    if (guild.id !== settings.guildId || entry.executorId === client.user?.id) return;
    queue('Auditoria do Discord', `Evento: ${entry.action}\nResponsável: ${entry.executorId || 'não informado'}\nAlvo: ${entry.targetId || 'não informado'}\nMotivo: ${entry.reason || 'não informado'}\nID: ${entry.id}`);
  });
  async function flush() {
    if (busy || stopped || !client.isReady()) return; busy = true;
    try {
      const channel = await client.channels.fetch(DISCORD_LOG_CHANNEL);
      for (const row of db.prepare('SELECT id,payload FROM outbox ORDER BY id LIMIT 10').all()) {
        await channel.send({ ...JSON.parse(row.payload), nonce: `al${row.id}`, enforceNonce: true });
        db.prepare('DELETE FROM outbox WHERE id=?').run(row.id);
      }
      db.prepare('DELETE FROM snapshots WHERE seen<?').run(Date.now() - 30*86400000);
    } catch { console.error('Logs Discord: entrega pendente; nova tentativa automática.'); }
    finally { busy = false; }
  }
  const timer = setInterval(flush, 3000); timer.unref();
  console.log('Logs Discord: registro privado habilitado.');
  return () => { stopped = true; clearInterval(timer); /* process exit closes SQLite after in-flight sends */ };
}
