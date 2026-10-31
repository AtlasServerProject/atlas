import { REST, Routes } from 'discord.js';
import { config } from './config.js';
import { commands } from './commands.js';

try {
  const settings = config();
  const rest = new REST({ version: '10' }).setToken(settings.token);
  // POST faz upsert por nome: não exclui comandos de outros módulos da aplicação.
  for (const command of commands) await rest.post(Routes.applicationGuildCommands(settings.applicationId, settings.guildId), { body: command });
  console.log(`${commands.length} comandos registrados no servidor configurado.`);
} catch { console.error('Registro falhou. Verifique IDs, token, instalação e permissões.'); process.exitCode = 1; }
