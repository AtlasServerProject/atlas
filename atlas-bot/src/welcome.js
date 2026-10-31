import { ChannelType, EmbedBuilder, PermissionFlagsBits } from 'discord.js';

const textChannel = channel => channel && [ChannelType.GuildText, ChannelType.GuildAnnouncement].includes(channel.type);
const welcomeName = name => name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z]/g, '');

export async function resolveWelcomeChannel(guild, settings) {
  let channel;
  if (settings.welcomeChannelId) {
    try { channel = await guild.channels.fetch(settings.welcomeChannelId); }
    catch { throw new Error('Canal configurado de boas-vindas inacessível. Confira DISCORD_WELCOME_CHANNEL_ID e Ver canal.'); }
  } else {
    await guild.channels.fetch();
    const matches = guild.channels.cache.filter(item => textChannel(item)
      && ['boasvindas', 'bemvindo', 'bemvindos'].includes(welcomeName(item.name)));
    if (matches.size > 1) throw new Error('Há mais de um canal de boas-vindas. Configure DISCORD_WELCOME_CHANNEL_ID para escolher o destino.');
    channel = matches.first();
    if (!channel) throw new Error('Canal de boas-vindas não encontrado. Configure DISCORD_WELCOME_CHANNEL_ID ou use boas-vindas/bem-vindo.');
  }
  if (!textChannel(channel) || channel.guildId !== settings.guildId) throw new Error('Canal de boas-vindas inválido ou de outro servidor.');
  return channel;
}

export async function checkWelcomePermissions(channel, guild) {
  const bot = guild.members.me || await guild.members.fetchMe();
  const permissions = channel.permissionsFor(bot);
  const required = [
    [PermissionFlagsBits.ViewChannel, 'Ver canal'],
    [PermissionFlagsBits.SendMessages, 'Enviar mensagens'],
    [PermissionFlagsBits.EmbedLinks, 'Inserir links (mensagem com imagem)'],
  ];
  const missing = required.filter(([flag]) => !permissions?.has(flag)).map(([, label]) => label);
  if (missing.length) throw new Error(`Faltam permissões do bot no canal de boas-vindas: ${missing.join(', ')}.`);
}

export async function repairWelcomePermissions(guild, settings) {
  const channel = await resolveWelcomeChannel(guild, settings);
  const bot = guild.members.me || await guild.members.fetchMe();
  await channel.permissionOverwrites.edit(bot.id, {
    ViewChannel: true, SendMessages: true, EmbedLinks: true,
  }, { reason: 'Correção de boas-vindas solicitada pelo dono do Atlas' });
  return channel;
}

export async function diagnoseWelcome(guild, settings, membersIntent) {
  const lines = [settings.welcomeEnabled === false ? 'Boas-vindas desativadas por configuração.' : 'Boas-vindas habilitadas.'];
  lines.push(membersIntent ? 'Evento de novos membros: habilitado.' : 'Evento de novos membros: desativado. Ative Server Members Intent no Developer Portal e reinicie o bot.');
  try {
    const channel = await resolveWelcomeChannel(guild, settings);
    lines.push(`Destino: <#${channel.id}> (${settings.welcomeChannelId ? 'ID configurado' : 'detectado pelo nome'}).`);
    await checkWelcomePermissions(channel, guild);
    lines.push('Permissões de envio e imagem: OK.');
  } catch (error) { lines.push(error.message); }
  lines.push('O envio automático acontece na entrada de novos membros; não ao ficar online ou reiniciar o bot.');
  return lines.join('\n');
}

export async function welcomeMember(member, settings) {
  if (member.guild.id !== settings.guildId || member.user.bot || settings.welcomeEnabled === false) return;
  const channel = await resolveWelcomeChannel(member.guild, settings);
  await checkWelcomePermissions(channel, member.guild);
  const channels = member.guild.channels.cache;
  const rules = channels.find(c => c.name === '📜・regras');
  const guide = channels.find(c => c.name === '📥・como-jogar');
  const embed = new EmbedBuilder().setColor(0x78ddff)
    .setTitle('✨ Bem-vindo ao Atlas Cobblemon!')
    .setDescription(`Sua aventura começa aqui, <@${member.id}>!\n\n📜 Confira ${rules ? `<#${rules.id}>` : 'o canal de regras'}.\n📥 Consulte ${guide ? `<#${guide.id}>` : 'o canal como-jogar'} para saber como começar.\n\nPrepare sua equipe, conheça outros treinadores e explore o mundo Atlas!`)
    .setThumbnail(member.user.displayAvatarURL())
    .setFooter({ text: 'Atlas Cobblemon • Uma nova aventura espera por você' });
  try {
    await channel.send({ content: `👋 <@${member.id}>, seja bem-vindo!`, embeds: [embed], allowedMentions: { parse: [], users: [member.id] } });
  } catch (error) { throw new Error(`Envio de boas-vindas recusado pelo Discord (código ${error.code || 'rede'}). Confira canal e permissões.`); }
}
