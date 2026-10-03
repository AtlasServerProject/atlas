import { ChannelType, PermissionFlagsBits } from 'discord.js';

export const layout = [
  { name: '📌 ATLAS • INFORMAÇÕES', aliases: ['ATLAS • INFORMAÇÕES'], channels: ['👋・boas-vindas', '📜・regras', '📣・avisos', '📥・como-jogar'], readOnly: true },
  { name: '🌿 ATLAS • COMUNIDADE', aliases: ['Canais de Texto', 'ATLAS • COMUNIDADE'], channels: ['💬・geral', '❓・duvidas', '💡・sugestoes', '📸・aventuras', '🤝・trocas'], readOnly: false },
  { name: '🔊 ATLAS • VOZ', aliases: ['Canais de Voz'], channels: ['🌳・Praça Emerald', '🧭・Exploração', '⚔️・Batalhas'], voice: true, readOnly: false },
];
export const roles = ['Treinador', 'Avisos Atlas'];
const colors = { Treinador: 0x2ecc71, 'Avisos Atlas': 0xf1c40f };
export function preview() {
  return 'Estrutura Atlas Cobblemon:\n' + layout.map(c => `${c.name}: ${c.channels.join(', ')}`).join('\n')
    + '\nCargos sem privilégios: ' + roles.join(', ')
    + '\nReaproveita e estiliza os canais padrão geral/Geral e as categorias existentes; não exclui canais. Execute /estrutura confirmar:true para aplicar.';
}
export async function applyStructure(guild) {
  await guild.channels.fetch();
  await guild.roles.fetch();
  const created = [];
  for (const name of roles) {
    if (!guild.roles.cache.some(r => r.name === name)) {
      await guild.roles.create({ name, colors: { primaryColor: colors[name] }, permissions: [], reason: 'Estrutura Atlas solicitada pelo dono' });
      created.push(`cargo ${name}`);
    }
  }
  for (const group of layout) {
    let category = guild.channels.cache.find(c => c.type === ChannelType.GuildCategory && (c.name === group.name || group.aliases.includes(c.name)));
    if (!category) {
      category = await guild.channels.create({ name: group.name, type: ChannelType.GuildCategory });
      created.push(group.name);
    } else if (category.name !== group.name) {
      await category.setName(group.name);
      created.push(`categoria ${group.name}`);
    }
    for (const name of group.channels) {
      const type = group.voice ? ChannelType.GuildVoice : ChannelType.GuildText;
      const oldName = name.split('・')[1];
      let channel = guild.channels.cache.find(c => c.type === type && c.name === name && c.parentId === category.id);
      if (!channel) channel = guild.channels.cache.find(c => c.type === type &&
        (c.name === oldName || (name === '🌳・Praça Emerald' && c.name === 'Geral')));
      if (channel) {
        if (channel.name !== name || channel.parentId !== category.id) {
          await channel.edit({ name, parent: category.id, lockPermissions: false, reason: 'Organização visual Atlas' });
          created.push(name);
        }
        continue;
      }
      await guild.channels.create({ name, type, parent: category.id,
        topic: group.voice ? undefined : `Atlas Cobblemon • ${oldName.replaceAll('-', ' ')}`,
        permissionOverwrites: group.readOnly ? [
          { id: guild.id, deny: [PermissionFlagsBits.SendMessages, PermissionFlagsBits.CreatePublicThreads, PermissionFlagsBits.CreatePrivateThreads, PermissionFlagsBits.SendMessagesInThreads] },
          { id: guild.members.me.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
        ] : [] });
      created.push(name);
    }
  }
  return created.length ? `Organizados: ${created.join(', ')}` : 'A estrutura já existe.';
}
