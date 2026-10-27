import { readFile, writeFile } from 'node:fs/promises';
const clientId = process.argv[2];
if (
  !clientId ||
  !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clientId) ||
  /^0{8}-0{4}-0{4}-0{4}-0{12}$/.test(clientId)
)
  throw new Error(
    'Informe somente o Application (client) ID público do aplicativo Atlas. Não informe Client Secret.',
  );
const path = new URL('../apps/desktop/resources/launcher-config.json', import.meta.url);
const config = JSON.parse(await readFile(path, 'utf8'));
config.microsoftClientId = clientId;
await writeFile(path, JSON.stringify(config, null, 2) + '\n');
console.log('Client ID público configurado. Execute npm run build ou npm run package:windows.');
