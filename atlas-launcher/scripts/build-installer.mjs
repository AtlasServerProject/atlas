import { checkInstallerIcon } from './check-installer-icon.mjs';
import { spawnSync } from 'node:child_process';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
const root = resolve('.'),
  version = JSON.parse(await readFile('apps/desktop/package.json', 'utf8')).version;
const tools = join(root, 'artifacts/nsis-tools/root/usr');
const output = join(root, 'artifacts/installer', `Atlas-Launcher-${version}-Setup-x64.exe`);
await mkdir(join(root, 'artifacts/installer'), { recursive: true });
await writeFile(
  join(root, 'artifacts/windows/Atlas Launcher-win32-x64/LEIA-ME.txt'),
  `ATLAS LAUNCHER ${version}\r\n\r\nUse o atalho Atlas Launcher criado pelo instalador. O aplicativo instalado baixa atualizações verificadas e as aplica ao fechar, depois de encerrar o Minecraft. Não é necessário extrair novos ZIPs.\r\nA pasta do aplicativo é separada dos dados do jogo. Não apague seus dados locais ao atualizar.\r\nSite oficial: https://www.atlascobblemon.com.br/how-to-play\r\n`,
);
const result = spawnSync(
  join(tools, 'bin/makensis'),
  [
    '-V3',
    `-DAPP_VERSION=${version}`,
    `-DEXE_VERSION=${version}.0`,
    `-DATLAS_ICON=${join(root, 'apps/desktop/assets/atlas.ico')}`,
    `-DAPP_PAYLOAD=${join(root, 'artifacts/windows/Atlas Launcher-win32-x64')}`,
    `-DINSTALLER_OUTPUT=${output}`,
    join(root, 'installer/atlas.nsi'),
  ],
  { env: { ...process.env, NSISDIR: join(tools, 'share/nsis') }, stdio: 'inherit' },
);
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
await checkInstallerIcon(output, join(root, 'apps/desktop/assets/atlas.ico'));
console.log(output);
