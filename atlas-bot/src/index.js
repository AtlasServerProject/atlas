import { Client, Events, GatewayIntentBits, REST, Routes, ApplicationFlags } from 'discord.js';
import { config } from './config.js';
import { createHandler, publish } from './commands.js';
import { createBridge } from './bridge.js';
import { assignMemberRole } from './member-role.js';
import { welcomeMember, diagnoseWelcome } from './welcome.js';

import { createMinecraftStatus, startMinecraftPresence } from './minecraft-status.js';

import { startStatusChannels } from './status-channels.js';
import { createNews, startNews } from './news.js';

let settings;
try { settings = config(); } catch (error) { console.error(error.message); process.exit(1); }
const intents = [GatewayIntentBits.Guilds];
if (settings.welcomeEnabled || settings.memberRoleId) {
  try {
    const application = await new REST().setToken(settings.token).get(Routes.currentApplication());
    if (application.flags & (ApplicationFlags.GatewayGuildMembers | ApplicationFlags.GatewayGuildMembersLimited)) {
      intents.push(GatewayIntentBits.GuildMembers);
      console.log('Boas-vindas: eventos de entrada habilitados.');
    } else console.error('Boas-vindas pendentes: ative Server Members Intent no Developer Portal e reinicie o bot.');
  } catch { console.error('Falha ao verificar o intent de membros.'); process.exit(1); }
}
const client = new Client({ intents, allowedMentions: { parse: [] } });
client.on(Events.GuildMemberAdd, member => {
  assignMemberRole(member, settings).catch(() => console.error('Falha ao atribuir Membro. Verifique cargo e hierarquia.'));
  welcomeMember(member, settings).catch(error => console.error(`Boas-vindas: ${error.message}`));
});
const minecraft = createMinecraftStatus(settings);
let stopMinecraft;
let stopStatusChannels;
let stopNews;
const news = createNews(client, settings);
let bridge;
client.on(Events.InteractionCreate, interaction => {
  createInteraction(interaction).catch(() => console.error('Falha ao responder à interação.'));
});
const createInteraction = createHandler(client, settings, minecraft, news);
client.on(Events.Error, () => console.error('Erro na conexão com o Discord.'));
client.once(Events.ClientReady, () => {
  if (!client.guilds.cache.has(settings.guildId)) {
    console.error('Instale o bot no servidor configurado.'); client.destroy(); process.exitCode = 1; return;
  }
  console.log('Atlas-bot conectado.');
  const guild = client.guilds.cache.get(settings.guildId);
  if (settings.welcomeEnabled) {
    diagnoseWelcome(guild, settings, client.options.intents.has(GatewayIntentBits.GuildMembers))
      .then(report => console.log(report.replace(/<#(\d+)>/g, 'canal $1')))
      .catch(() => console.error('Falha ao diagnosticar boas-vindas. Confira a configuração do servidor.'));
  }
  stopMinecraft = startMinecraftPresence(client, minecraft);
  stopStatusChannels = startStatusChannels(client, settings, minecraft);
  stopNews = startNews(news, settings);
  if (settings.bridgeSecret) {
    bridge = createBridge(settings.bridgeSecret, message => publish(client, settings, message));
    bridge.on('error', () => { console.error('Falha ao iniciar a integração local.'); client.destroy(); process.exitCode = 1; });
    bridge.listen(settings.bridgePort, '127.0.0.1', () => console.log('Integração Minecraft disponível apenas em localhost.'));
  }
});
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => { stopMinecraft?.(); stopStatusChannels?.(); stopNews?.(); bridge?.close(); client.destroy(); });
client.login(settings.token).catch(() => { console.error('Falha ao conectar. Verifique o token e a rede.'); process.exitCode = 1; client.destroy(); });
