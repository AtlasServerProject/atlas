import { packager } from '@electron/packager';
import { cp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
const metadata = JSON.parse(await readFile(join(root, 'apps/desktop/package.json'), 'utf8'));
const staging = join(root, 'artifacts/staging');
await rm(staging, { recursive: true, force: true });
await mkdir(staging, { recursive: true });
await cp(join(root, 'apps/desktop/dist'), join(staging, 'dist'), { recursive: true });
await writeFile(
  join(staging, 'package.json'),
  JSON.stringify(
    {
      name: 'atlas-launcher',
      productName: 'Atlas Launcher',
      version: metadata.version,
      main: 'dist/main.cjs',
      description: 'Atlas Cobblemon Launcher — prévia de desenvolvimento',
      author: 'Atlas Cobblemon',
    },
    null,
    2,
  ),
);
const output = await packager({
  dir: staging,
  name: 'Atlas Launcher',
  executableName: 'AtlasLauncher',
  platform: 'win32',
  arch: 'x64',
  electronVersion: metadata.devDependencies.electron,
  appVersion: metadata.version,
  appCopyright: 'Atlas Cobblemon',
  icon: join(root, 'apps/desktop/assets/atlas.ico'),
  out: join(root, 'artifacts/windows'),
  overwrite: true,
  asar: { unpack: '**/*.mp4' },
  prune: false,
  download: {
    checksums: JSON.parse(
      await readFile(join(root, 'node_modules/electron/checksums.json'), 'utf8'),
    ),
  },
});
for (const directory of output) {
  await writeFile(
    join(directory, 'LEIA-ME.txt'),
    'ATLAS LAUNCHER ' +
      metadata.version +
      ' — PRÉVIA WINDOWS x64\r\n\r\nExtraia toda esta pasta e abra AtlasLauncher.exe. Não execute de dentro do ZIP.\r\nMantenha o executável junto das DLLs, resources e demais arquivos.\r\nNão precisa instalar Node.js ou Java para abrir esta prévia.\r\n\r\nDownload e instalação de Minecraft 1.21.1, Fabric 0.18.0, Java 21 e modpack Atlas integrados. Login oficial depende do cadastro Microsoft do Atlas (Client ID próprio). Sem ele, o jogo permanece bloqueado.\r\nEste pacote não possui assinatura Authenticode e ainda precisa de teste nativo Windows.\r\nNão desative o antivírus ou as proteções do sistema para executá-lo.\r\n',
  );
  console.log(directory);
}
await rm(staging, { recursive: true, force: true });
