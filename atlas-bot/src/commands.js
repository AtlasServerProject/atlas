import { SlashCommandBuilder, PermissionFlagsBits, MessageFlags } from 'discord.js';
import { preview, applyStructure } from './structure.js';
import { ownerCommand, isOwnerContext, administer } from './admin.js';

import { statusText } from './minecraft-status.js';

export const commands = [
  new SlashCommandBuilder().setName('online').setDescription('Consultar jogadores online no Minecraft Atlas.'),
  new SlashCommandBuilder().setName('ping').setDescription('Verificar a conexão do Atlas-bot.'),
  new SlashCommandBuilder().setName('ajuda').setDescription('Conhecer os comandos do Atlas-bot.'),
  new SlashCommandBuilder().setName('servidor').setDescription('Consultar o endereço do Minecraft Atlas.'),
  new SlashCommandBuilder().setName('como-jogar').setDescription('Consultar as instruções de acesso ao Atlas.'),
  new SlashCommandBuilder().setName('estrutura').setDescription('Prévia ou criação dos canais e cargos Atlas.')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addBooleanOption(o => o.setName('confirmar').setDescription('Criar os canais e cargos ausentes.')),
  new SlashCommandBuilder().setName('aviso').setDescription('Publicar um aviso no canal configurado.')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addStringOption(o => o.setName('texto').setDescription('Conteúdo do aviso, sem notificações em massa.').setRequired(true).setMaxLength(1800)),
].map(c => c.toJSON());
commands.push(ownerCommand);

export async function publish(client, settings, content) {
  if (!settings.channelId) throw new Error('Canal de avisos não configurado.');
  const channel = await client.channels.fetch(settings.channelId);
  if (!channel || channel.guildId !== settings.guildId || !channel.isTextBased() || !channel.send) throw new Error('Canal de avisos inválido.');
  await channel.send({ content, allowedMentions: { parse: [] } });
}

export function createHandler(client, settings, minecraft) {
  let organizing = false;
  return async interaction => {
    if (!interaction.isChatInputCommand()) return;
    if (interaction.guildId !== settings.guildId) {
      await interaction.reply({ content: 'Este bot atende somente ao Discord do Atlas.', flags: MessageFlags.Ephemeral });
      return;
    }
    const name = interaction.commandName;
    const admin = ['aviso', 'estrutura', 'dono'].includes(name);
    if (admin && !isOwnerContext(interaction, settings)) {
      await interaction.reply({ content: 'Comando exclusivo do DONO, no canal privado configurado.', flags: MessageFlags.Ephemeral });
      return;
    }
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    try {
      let content;
      switch (name) {
        case 'online': content = statusText(await minecraft.read()); break;
        case 'dono': content = await administer(interaction, settings); break;
        case 'ping': content = `Atlas-bot conectado. Latência do gateway: ${client.ws.ping} ms. Isto não mede o Minecraft.`; break;
        case 'ajuda': content = '/ping • /online • /servidor • /como-jogar\nDONO no canal privado: /dono, /estrutura (prévia por padrão) e /aviso.'; break;
        case 'servidor': content = `Minecraft Atlas: ${settings.address}\nMinecraft Java 1.21.1 com o modpack do servidor.`; break;
        case 'como-jogar': content = `Instale o modpack oficial do Atlas e adicione o servidor ${settings.address}.\n${settings.modpack ? `Modpack: ${settings.modpack}` : 'Link do modpack ainda não configurado; consulte a equipe.'}\nO guia detalhado está em elaboração.`; break;
        case 'aviso':
          await publish(client, settings, interaction.options.getString('texto', true));
          content = 'Aviso publicado.'; break;
        case 'estrutura':
          if (!interaction.options.getBoolean('confirmar')) { content = preview(); break; }
          if (organizing) { content = 'Uma criação de estrutura já está em andamento.'; break; }
          organizing = true;
          try { content = await applyStructure(interaction.guild); } finally { organizing = false; }
          break;
        default: content = 'Comando não reconhecido.';
      }
      await interaction.editReply({ content, allowedMentions: { parse: [] } });
    } catch {
      console.error(`Falha no comando ${name}. Verifique configuração e permissões.`);
      await interaction.editReply('Não foi possível concluir. Verifique a configuração e as permissões do bot. Se a estrutura foi criada parcialmente, executar novamente cria somente os elementos ausentes.');
    }
  };
}
