import { status } from 'minecraft-server-util';
import { ActivityType } from 'discord.js';

export function createMinecraftStatus(settings, query = status, now = Date.now) {
  let cached;
  let pending;
  async function read() {
    if (cached && now() - cached.checkedAt < 10000) return cached;
    if (pending) return pending;
    pending = (async () => {
      try {
        const result = await query(settings.minecraftHost, settings.minecraftPort, { timeout: 5000, enableSRV: false });
        const { online, max } = result.players;
        if (!Number.isInteger(online) || online < 0 || !Number.isInteger(max) || max < 0) throw new Error('Invalid count');
        cached = { available: true, online, max, checkedAt: now() };
      } catch { cached = { available: false, checkedAt: now() }; }
      return cached;
    })();
    try { return await pending; } finally { pending = undefined; }
  }
  return { read };
}

export function statusText(result) {
  return result.available
    ? `🟢 Minecraft Atlas: **${result.online}/${result.max} jogadores online**.\nConsultado <t:${Math.floor(result.checkedAt / 1000)}:R>.`
    : '🟠 Minecraft indisponível ou sem resposta. Não foi possível consultar os jogadores.';
}

export function startMinecraftPresence(client, monitor) {
  let stopped = false;
  let timer;
  async function update() {
    try {
      const result = await monitor.read();
      if (!stopped) client.user.setPresence({ status: 'online', activities: [{ type: ActivityType.Watching,
        name: result.available ? `Minecraft: ${result.online}/${result.max} online` : 'Minecraft: indisponível' }] });
    } catch { console.error('Falha ao atualizar o contador Minecraft.'); }
    finally { if (!stopped) timer = setTimeout(update, 30000); }
  }
  void update();
  return () => { stopped = true; clearTimeout(timer); };
}
