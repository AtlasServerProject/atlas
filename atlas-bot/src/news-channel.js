import { ChannelType, PermissionFlagsBits } from 'discord.js';

export async function prepareNewsChannel(guild) {
  await guild.channels.fetch();
  const group = guild.channels.cache.find(channel => channel.type === ChannelType.GuildCategory
    && ['📌 ATLAS • INFORMAÇÕES', 'ATLAS • INFORMAÇÕES'].includes(channel.name))
    || await guild.channels.create({ name: '📌 ATLAS • INFORMAÇÕES', type: ChannelType.GuildCategory,
      reason: 'Categoria de novidades solicitada pelo dono do Atlas' });
  const everyone = {
    ViewChannel: true, ReadMessageHistory: true, SendMessages: false,
    CreatePublicThreads: false, CreatePrivateThreads: false, SendMessagesInThreads: false,
  };
  const bot = { ViewChannel: true, ReadMessageHistory: true, SendMessages: true, EmbedLinks: true };
  let channel = guild.channels.cache.find(item => item.type === ChannelType.GuildText
    && ['📰・novidades', 'novidades'].includes(item.name));
  if (channel) {
    // Preserve unrelated overwrites while making this channel read-only for members.
    await channel.edit({ name: '📰・novidades', parent: group.id, lockPermissions: false,
      topic: 'Notas de atualização do Atlas • Novidades do site e mudanças para jogadores',
      reason: 'Canal de novidades solicitado pelo dono do Atlas' });
    await channel.permissionOverwrites.edit(guild.id, everyone);
    await channel.permissionOverwrites.edit(guild.members.me.id, bot);
  } else {
    channel = await guild.channels.create({ name: '📰・novidades', type: ChannelType.GuildText, parent: group.id,
      topic: 'Notas de atualização do Atlas • Novidades do site e mudanças para jogadores',
      reason: 'Canal de novidades solicitado pelo dono do Atlas',
      permissionOverwrites: [
        { id: guild.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.ReadMessageHistory],
          deny: [PermissionFlagsBits.SendMessages, PermissionFlagsBits.CreatePublicThreads, PermissionFlagsBits.CreatePrivateThreads, PermissionFlagsBits.SendMessagesInThreads] },
        { id: guild.members.me.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.ReadMessageHistory, PermissionFlagsBits.SendMessages, PermissionFlagsBits.EmbedLinks] },
      ],
    });
  }
  return channel;
}
