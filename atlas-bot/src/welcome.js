import { ChannelType, EmbedBuilder } from 'discord.js';

export async function welcomeMember(member, settings) {
  if (member.guild.id !== settings.guildId || member.user.bot || !settings.welcomeChannelId) return;
  const channel = await member.guild.channels.fetch(settings.welcomeChannelId);
  if (!channel || channel.guildId !== settings.guildId || channel.type !== ChannelType.GuildText) throw new Error('Canal de boas-vindas inválido.');
  const channels = member.guild.channels.cache;
  const rules = channels.find(c => c.name === '📜・regras');
  const guide = channels.find(c => c.name === '📥・como-jogar');
  const embed = new EmbedBuilder().setColor(0x2ecc71)
    .setTitle('🌿 Bem-vindo ao Atlas Cobblemon!')
    .setDescription(`Sua aventura começa aqui, <@${member.id}>!\n\n📜 Confira ${rules ? `<#${rules.id}>` : 'o canal de regras'}.\n📥 Consulte ${guide ? `<#${guide.id}>` : 'o canal como-jogar'} para saber como começar.\n\nPrepare sua equipe, conheça outros treinadores e explore o mundo Atlas!`)
    .setThumbnail(member.user.displayAvatarURL())
    .setFooter({ text: 'Atlas Cobblemon • Uma nova aventura espera por você' });
  await channel.send({ content: `👋 <@${member.id}>, seja bem-vindo!`, embeds: [embed], allowedMentions: { parse: [], users: [member.id] } });
}
