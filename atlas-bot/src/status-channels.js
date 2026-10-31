import { ChannelType, PermissionFlagsBits } from 'discord.js';

export function counterNames(memberCount, result, address) {
  return [
    `👥・Discord: ${memberCount}`,
    address && address !== 'Endereço em configuração' ? `🌐・${address}`.slice(0, 100) : null,
    result.available ? `🟢・Online: ${result.online}/${result.max}` : '🟠・Minecraft indisponível',
  ];
}

export async function updateStatusChannels(client, settings, monitor) {
  const guild = await client.guilds.fetch(settings.guildId);
  await guild.channels.fetch();
  const me = await guild.members.fetchMe();
  const permissions = [
    { id: guild.id, allow: [PermissionFlagsBits.ViewChannel], deny: [PermissionFlagsBits.Connect] },
    { id: me.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.ManageChannels, PermissionFlagsBits.Connect] },
  ];
  let category = guild.channels.cache.find(c => c.type === ChannelType.GuildCategory && c.name === 'STATUS');
  if (!category) category = await guild.channels.create({ name: 'STATUS', type: ChannelType.GuildCategory, permissionOverwrites: permissions });
  const result = await monitor.read();
  const names = counterNames(guild.memberCount, result, settings.address);
  const prefixes = ['👥・', '🌐・', ['🟢・Online:', '🟠・Minecraft indisponível']];
  for (let i = 0; i < names.length; i++) {
    if (!names[i]) continue;
    const prefixesForChannel = Array.isArray(prefixes[i]) ? prefixes[i] : [prefixes[i]];
    let channel = guild.channels.cache.find(c => c.parentId === category.id && c.type === ChannelType.GuildVoice && prefixesForChannel.some(p => c.name.startsWith(p)));
    if (!channel) {
      channel = await guild.channels.create({ name: names[i], type: ChannelType.GuildVoice, parent: category.id, permissionOverwrites: permissions });
    } else if (channel.name !== names[i]) await channel.setName(names[i], 'Atualização dos contadores Atlas');
  }
  return names;
}

export function startStatusChannels(client, settings, monitor) {
  let stopped = false;
  let timer;
  async function update() {
    try { await updateStatusChannels(client, settings, monitor); }
    catch { console.error('Falha ao atualizar canais STATUS. Verifique permissões e conexão.'); }
    finally { if (!stopped) timer = setTimeout(update, 310000); }
  }
  void update();
  return () => { stopped = true; clearTimeout(timer); };
}
