import { SlashCommandBuilder, PermissionFlagsBits, MessageFlags, GatewayIntentBits } from 'discord.js';
import { preview, applyStructure } from './structure.js';
import { ownerCommand, isOwnerContext, administer } from './admin.js';

import { statusText } from './minecraft-status.js';
import { prepareNewsChannel } from './news-channel.js';
import { diagnoseWelcome, welcomeMember, repairWelcomePermissions } from './welcome.js';

export const commands = [
  new SlashCommandBuilder().setName('boas-vindas').setDescription('Diagnosticar o canal e testar as boas-vindas do Atlas.')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addBooleanOption(o => o.setName('corrigir').setDescription('Permitir ao bot ver o canal e enviar mensagens com imagem.'))
    .addBooleanOption(o => o.setName('testar').setDescription('Enviar uma mensagem de teste para você no canal de boas-vindas.')),
  new SlashCommandBuilder().setName('preparar-novidades').setDescription('Preparar o canal de novidades do Atlas.')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addBooleanOption(o => o.setName('confirmar').setDescription('Criar ou configurar o canal de novidades.')),
  new SlashCommandBuilder().setName('online').setDescription('Consultar jogadores online no Minecraft Atlas.'),
  new SlashCommandBuilder().setName('ping').setDescription('Verificar a conexão do Atlas-bot.'),
  new SlashCommandBuilder().setName('ajuda').setDescription('Conhecer os comandos do Atlas-bot.'),
  new SlashCommandBuilder().setName('servidor').setDescription('Consultar o endereço do Minecraft Atlas.'),
  new SlashCommandBuilder().setName('como-jogar').setDescription('Consultar as instruções de acesso ao Atlas.'),
  new SlashCommandBuilder().setName('novidades').setDescription('Ler a última atualização publicada no site Atlas.'),
  new SlashCommandBuilder().setName('publicar-novidade').setDescription('Revisar ou publicar uma novidade do site no Discord.')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
    .addStringOption(o => o.setName('id').setDescription('ID da nota; sem ID, usa a mais recente.').setMaxLength(60))
    .addBooleanOption(o => o.setName('confirmar').setDescription('Publicar no canal de novidades configurado.')),
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

export function createHandler(client, settings, minecraft, news) {
  let organizing = false;
  let preparingNews = false;
  return async interaction => {
    if (!interaction.isChatInputCommand()) return;
    if (interaction.guildId !== settings.guildId) {
      await interaction.reply({ content: 'Este bot atende somente ao Discord do Atlas.', flags: MessageFlags.Ephemeral });
      return;
    }
    const name = interaction.commandName;
    const admin = ['aviso', 'estrutura', 'dono', 'publicar-novidade', 'preparar-novidades', 'boas-vindas'].includes(name);
    if (admin && !isOwnerContext(interaction, settings)) {
      await interaction.reply({ content: 'Comando exclusivo do DONO, no canal privado configurado.', flags: MessageFlags.Ephemeral });
      return;
    }
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
    try {
      let content;
      switch (name) {
        case 'boas-vindas': {
          if (interaction.options.getBoolean('corrigir')) await repairWelcomePermissions(interaction.guild, settings);
          content = await diagnoseWelcome(interaction.guild, settings, client.options.intents.has(GatewayIntentBits.GuildMembers));
          if (interaction.options.getBoolean('testar')) {
            if (!settings.welcomeEnabled) { content += '\nTeste não enviado: boas-vindas desativadas.'; break; }
            const member = await interaction.guild.members.fetch(interaction.user.id);
            try {
              await welcomeMember(member, settings);
              content += '\nMensagem de teste enviada para você no canal de boas-vindas. O teste verifica o envio, não o recebimento automático de novas entradas.';
            } catch (error) { content += `\nTeste não enviado: ${error.message}`; }
          }
          break;
        }
        case 'preparar-novidades': {
          if (!interaction.options.getBoolean('confirmar')) {
            content = 'Cria ou reaproveita 📰・novidades em 📌 ATLAS • INFORMAÇÕES, com leitura para membros e envio de novidades pelo bot. Para aplicar: /preparar-novidades confirmar:true'; break;
          }
          if (preparingNews) { content = 'O canal de novidades já está sendo preparado.'; break; }
          preparingNews = true;
          try {
            const channel = await prepareNewsChannel(interaction.guild);
            settings.newsChannelId = channel.id;
            content = `Canal de novidades preparado: <#${channel.id}>. Para preservar a configuração após reinício, defina DISCORD_NEWS_CHANNEL_ID=${channel.id} no arquivo local do bot.`;
          } finally { preparingNews = false; }
          break;
        }
        case 'novidades':
        case 'publicar-novidade': {
          if (!news || !settings.newsFeedUrl) { content = 'Novidades do site ainda não configuradas.'; break; }
          const id = name === 'publicar-novidade' ? interaction.options.getString('id') : undefined;
          if (name === 'publicar-novidade' && interaction.options.getBoolean('confirmar')) {
            content = await news.publish(id);
            break;
          }
          const preview = await news.preview(id);
          await interaction.editReply({ ...preview.payload,
            content: name === 'publicar-novidade'
              ? `Prévia privada. Para publicar: /publicar-novidade id:${preview.id} confirmar:true` : undefined });
          return;
        }
        case 'online': content = statusText(await minecraft.read()); break;
        case 'dono': content = await administer(interaction, settings); break;
        case 'ping': content = `Atlas-bot conectado. Latência do gateway: ${client.ws.ping} ms. Isto não mede o Minecraft.`; break;
        case 'ajuda': content = '/ping • /online • /servidor • /como-jogar • /novidades\nDONO no canal privado: /dono, /estrutura, /aviso, /boas-vindas, /preparar-novidades e /publicar-novidade.'; break;
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
