export function config(env = process.env) {
  for (const key of ['DISCORD_TOKEN', 'DISCORD_APPLICATION_ID', 'DISCORD_GUILD_ID']) {
    if (!env[key]?.trim()) throw new Error(`Configure ${key}.`);
  }
  for (const key of ['DISCORD_APPLICATION_ID', 'DISCORD_GUILD_ID', 'DISCORD_ANNOUNCEMENTS_CHANNEL_ID', 'DISCORD_OWNER_ID', 'DISCORD_OWNER_CHANNEL_ID', 'DISCORD_WELCOME_CHANNEL_ID', 'DISCORD_MEMBER_ROLE_ID']) {
    if (env[key] && !/^\d{17,20}$/.test(env[key])) throw new Error(`${key} deve ser um ID do Discord.`);
  }
  if (!!env.DISCORD_OWNER_ID !== !!env.DISCORD_OWNER_CHANNEL_ID) throw new Error('Configure juntos DISCORD_OWNER_ID e DISCORD_OWNER_CHANNEL_ID.');
  const minecraftPort = Number(env.MINECRAFT_STATUS_PORT || 25565);
  if (!Number.isInteger(minecraftPort) || minecraftPort < 1 || minecraftPort > 65535) throw new Error('MINECRAFT_STATUS_PORT inválida.');
  const secret = env.ATLAS_BRIDGE_SECRET || '';
  if (secret && secret.length < 32) throw new Error('ATLAS_BRIDGE_SECRET precisa de pelo menos 32 caracteres.');
  if (secret && !env.DISCORD_ANNOUNCEMENTS_CHANNEL_ID) throw new Error('Configure o canal de avisos antes de habilitar a integração.');
  const port = Number(env.ATLAS_BRIDGE_PORT || 8787);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('ATLAS_BRIDGE_PORT inválida.');
  if (env.MODPACK_URL) {
    const url = new URL(env.MODPACK_URL);
    if (url.protocol !== 'https:') throw new Error('MODPACK_URL deve usar HTTPS.');
  }
  return { token: env.DISCORD_TOKEN.trim(), applicationId: env.DISCORD_APPLICATION_ID,
    minecraftHost: env.MINECRAFT_STATUS_HOST || '127.0.0.1', minecraftPort,
    guildId: env.DISCORD_GUILD_ID, ownerId: env.DISCORD_OWNER_ID, ownerChannelId: env.DISCORD_OWNER_CHANNEL_ID,
    address: env.MINECRAFT_ADDRESS || 'Endereço em configuração',
    welcomeChannelId: env.DISCORD_WELCOME_CHANNEL_ID, memberRoleId: env.DISCORD_MEMBER_ROLE_ID,
    modpack: env.MODPACK_URL || '', channelId: env.DISCORD_ANNOUNCEMENTS_CHANNEL_ID,
    bridgeSecret: secret, bridgePort: port };
}
