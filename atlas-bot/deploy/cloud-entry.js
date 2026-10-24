import { Client, GatewayIntentBits } from 'discord.js';
import { cloudClientOptions } from '../src/cloud-profile.js';

process.env.ATLAS_CLOUD_MODE = 'true';
if (process.argv.includes('--check-runtime')) {
  const client = new Client({ ...cloudClientOptions(), intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers] });
  global.gc?.();
  console.log(`Cloud runtime OK (sem conexão): ${Math.ceil(process.memoryUsage().rss / 1024 / 1024)} MiB RSS`);
  await client.destroy();
} else {
  await import('../src/index.js');
}
