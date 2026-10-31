import { SlashCommandBuilder, ChannelType, PermissionFlagsBits } from 'discord.js';

const permissions = ['ViewChannel', 'SendMessages', 'ReadMessageHistory', 'Connect', 'Speak', 'ManageMessages', 'ManageChannels', 'ManageRoles', 'KickMembers', 'BanMembers', 'ModerateMembers', 'MentionEveryone'];
export const ownerCommand = new SlashCommandBuilder().setName('dono').setDescription('Administração exclusiva do dono no canal privado.')
  .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
  .addSubcommand(s => s.setName('canal').setDescription('Criar canal de texto ou voz.')
    .addStringOption(o => o.setName('nome').setDescription('Nome do canal').setRequired(true).setMaxLength(90))
    .addStringOption(o => o.setName('tipo').setDescription('Tipo').setRequired(true).addChoices({ name: 'Texto', value: 'texto' }, { name: 'Voz', value: 'voz' }))
    .addChannelOption(o => o.setName('categoria').setDescription('Categoria opcional; herda suas permissões').addChannelTypes(ChannelType.GuildCategory)))
  .addSubcommand(s => s.setName('cargo').setDescription('Criar um cargo sem privilégios iniciais.')
    .addStringOption(o => o.setName('nome').setDescription('Nome do cargo').setRequired(true).setMaxLength(90)))
  .addSubcommand(s => s.setName('atribuir').setDescription('Atribuir um cargo existente a um membro.')
    .addUserOption(o => o.setName('membro').setDescription('Membro').setRequired(true))
    .addRoleOption(o => o.setName('cargo').setDescription('Cargo').setRequired(true)))
  .addSubcommand(s => s.setName('permissao').setDescription('Alterar uma permissão de um cargo; opcionalmente em um canal.')
    .addRoleOption(o => o.setName('cargo').setDescription('Cargo alvo').setRequired(true))
    .addStringOption(o => o.setName('permissao').setDescription('Permissão').setRequired(true).addChoices(...permissions.map(p => ({ name: p, value: p }))))
    .addBooleanOption(o => o.setName('permitir').setDescription('Sim permite; não revoga no cargo ou nega no canal').setRequired(true))
    .addChannelOption(o => o.setName('canal').setDescription('Opcional: aplicar só neste canal').addChannelTypes(ChannelType.GuildText, ChannelType.GuildVoice, ChannelType.GuildCategory)))
  .toJSON();

export function isOwnerContext(interaction, settings) {
  return Boolean(settings.ownerId && settings.ownerChannelId && interaction.user?.id === settings.ownerId
    && interaction.channelId === settings.ownerChannelId && interaction.guildId === settings.guildId);
}

export async function administer(interaction, settings) {
  const guild = interaction.guild;
  const options = interaction.options;
  const reason = `Atlas-bot: solicitação do dono ${interaction.user.id}`;
  switch (options.getSubcommand()) {
    case 'canal': {
      const category = options.getChannel('categoria');
      const type = options.getString('tipo', true) === 'voz' ? ChannelType.GuildVoice : ChannelType.GuildText;
      const channel = await guild.channels.create({ name: options.getString('nome', true), type, parent: category?.id, reason });
      return `Canal criado: <#${channel.id}>. ${category ? 'Permissões herdadas da categoria.' : 'Permissões padrão do servidor.'}`;
    }
    case 'cargo': {
      const role = await guild.roles.create({ name: options.getString('nome', true), permissions: [], reason });
      return `Cargo criado: ${role.name} (ID ${role.id}).`;
    }
    case 'atribuir': {
      const role = await guild.roles.fetch(options.getRole('cargo', true).id);
      if (!role || !role.editable || role.managed || role.id === guild.id) return 'Este cargo não pode ser atribuído pelo bot. Verifique a hierarquia.';
      const member = await guild.members.fetch(options.getUser('membro', true).id);
      await member.roles.add(role, reason);
      return 'Cargo atribuído.';
    }
    case 'permissao': {
      const role = await guild.roles.fetch(options.getRole('cargo', true).id);
      const channel = options.getChannel('canal');
      const key = options.getString('permissao', true);
      if (!permissions.includes(key)) return 'Permissão não suportada.';
      if (!role || role.managed || !role.editable) return 'Este cargo não pode ser alterado pelo bot. Verifique a hierarquia.';
      // Evita bloquear o próprio console de administração ou expô-lo por sobrescrita direta.
      if (channel?.id === settings.ownerChannelId || channel?.id === interaction.channel?.parentId) return 'Gerencie as permissões do canal do dono e sua categoria diretamente no Discord.';
      const enabled = options.getBoolean('permitir', true);
      if (channel) {
        await channel.permissionOverwrites.edit(role.id, { [key]: enabled }, { reason });
      } else {
        const bits = enabled ? role.permissions.bitfield | PermissionFlagsBits[key] : role.permissions.bitfield & ~PermissionFlagsBits[key];
        await role.setPermissions(bits, reason);
      }
      return `Permissão ${key} ${enabled ? 'permitida' : channel ? 'negada' : 'revogada'} para ${role.name}${channel ? ` em <#${channel.id}>` : ' no servidor'}. Outras permissões/cargos podem afetar o acesso efetivo.`;
    }
    default: return 'Operação desconhecida.';
  }
}
