import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, rename, readdir, rm, stat, statfs } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import {
  TrustedTransport,
  downloadFile,
  limitedBytes,
  missingDownloadBytes,
  type DownloadFile,
} from './download';
import { ownedPath, safeRelative } from './paths';
import { extractArchive } from './archive';
export const GAME_ORIGINS = new Set([
  'https://piston-meta.mojang.com',
  'https://piston-data.mojang.com',
  'https://launchermeta.mojang.com',
  'https://launcher.mojang.com',
  'https://libraries.minecraft.net',
  'https://resources.download.minecraft.net',
  'https://meta.fabricmc.net',
  'https://maven.fabricmc.net',
  'https://api.adoptium.net',
  'https://github.com',
  'https://release-assets.githubusercontent.com',
  'https://objects.githubusercontent.com',
]);
export interface GamePlan {
  minecraftVersion: string;
  fabricVersion: string;
  versionId: string;
  vanilla: any;
  fabric: any;
  files: DownloadFile[];
  classPath: string[];
  natives: string[];
  assetIndexId: string;
  java: { url: string; size: number; hash: string };
  estimatedBytes: number;
}
function integer(value: unknown): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value <= 0)
    throw new Error('Tamanho oficial inválido.');
  return value;
}
function hash(value: unknown, algorithm: 'sha1' | 'sha256'): string {
  if (
    typeof value !== 'string' ||
    !(algorithm === 'sha1' ? /^[a-f0-9]{40}$/ : /^[a-f0-9]{64}$/).test(value)
  )
    throw new Error('Hash oficial inválido.');
  return value;
}
export function rulesAllow(
  rules: any[] | undefined,
  platform = 'windows',
  arch = 'x86_64',
): boolean {
  if (!rules) return true;
  let allowed = false;
  for (const rule of rules) {
    const matches =
      (!rule.os ||
        ((!rule.os.name || rule.os.name === platform) &&
          (!rule.os.arch || rule.os.arch === arch) &&
          (!rule.os.version || new RegExp(rule.os.version).test('10.0')))) &&
      (!rule.features || Object.entries(rule.features).every(([, value]) => value === false));
    if (matches) allowed = rule.action === 'allow';
  }
  return allowed;
}
export function mavenPath(name: string): string {
  if (!/^[a-zA-Z0-9_.+-]+:[a-zA-Z0-9_.+-]+:[a-zA-Z0-9_.+-]+(?::[a-zA-Z0-9_.+-]+)?$/.test(name))
    throw new Error('Biblioteca inválida.');
  const [group, artifact, version, classifier] = name.split(':');
  return `${group.replaceAll('.', '/')}/${artifact}/${version}/${artifact}-${version}${classifier ? '-' + classifier : ''}.jar`;
}
async function checkedJson(
  url: string,
  sha1: string,
  size: number,
  transport: TrustedTransport,
): Promise<any> {
  const response = await transport.fetch(url);
  if (!response.ok) throw new Error('Metadados oficiais indisponíveis.');
  const bytes = await limitedBytes(response, size);
  if (bytes.length !== size || createHash('sha1').update(bytes).digest('hex') !== sha1)
    throw new Error('Integridade dos metadados oficiais inválida.');
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}
export async function resolveGamePlan(
  minecraftVersion: string,
  fabricVersion: string,
  transport = new TrustedTransport(GAME_ORIGINS),
): Promise<GamePlan> {
  if (minecraftVersion !== '1.21.1' || !/^0\.\d+\.\d+$/.test(fabricVersion))
    throw new Error('Versão de jogo não suportada.');
  const index = (await transport.json(
    'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json',
  )) as any;
  const item = index.versions?.find((v: any) => v.id === minecraftVersion);
  if (!item || !/^https:\/\/piston-meta\.mojang\.com\//.test(item.url))
    throw new Error('Minecraft oficial não encontrado.');
  const response = await transport.fetch(item.url);
  if (!response.ok) throw new Error('Minecraft indisponível.');
  const versionBytes = await limitedBytes(response, 2 * 1024 ** 2);
  if (createHash('sha1').update(versionBytes).digest('hex') !== hash(item.sha1, 'sha1'))
    throw new Error('Metadados Minecraft corrompidos.');
  const vanilla = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(versionBytes));
  if (vanilla.id !== minecraftVersion || vanilla.javaVersion?.majorVersion !== 21)
    throw new Error('Requisitos Minecraft inesperados.');
  const fabric = (await transport.json(
    `https://meta.fabricmc.net/v2/versions/loader/${minecraftVersion}/${fabricVersion}/profile/json`,
  )) as any;
  if (
    fabric.inheritsFrom !== minecraftVersion ||
    fabric.id !== `fabric-loader-${fabricVersion}-${minecraftVersion}` ||
    fabric.mainClass !== 'net.fabricmc.loader.impl.launch.knot.KnotClient'
  )
    throw new Error('Perfil Fabric inválido.');
  const files: DownloadFile[] = [];
  const classPath: string[] = [];
  const natives: string[] = [];
  const add = (path: string, metadata: any, algorithm: 'sha1' | 'sha256' = 'sha1') => {
    safeRelative(path);
    const url = new URL(metadata.url);
    if (url.protocol !== 'https:' || !GAME_ORIGINS.has(url.origin))
      throw new Error('Biblioteca fora das fontes oficiais.');
    files.push({
      path,
      url: url.href,
      size: integer(metadata.size),
      hash: hash(metadata[algorithm], algorithm),
      algorithm,
    });
  };
  const clientPath = `versions/${minecraftVersion}/${minecraftVersion}.jar`;
  add(clientPath, vanilla.downloads.client);
  for (const library of vanilla.libraries) {
    if (!rulesAllow(library.rules) || /natives-windows-(arm64|x86)$/.test(library.name)) continue;
    const artifact = library.downloads?.artifact;
    if (artifact) {
      const path = 'libraries/' + artifact.path;
      add(path, artifact);
      classPath.push(path);
      if (library.name.includes('natives-windows')) natives.push(path);
    }
  }
  for (const library of fabric.libraries) {
    const relative = mavenPath(library.name);
    const url = new URL(relative, library.url).href;
    let metadata = library;
    if (!library.sha1 && !library.sha256) {
      const checksumResponse = await transport.fetch(url + '.sha1');
      if (!checksumResponse.ok) throw new Error('Fabric não forneceu hash da biblioteca.');
      const checksum = Buffer.from(await limitedBytes(checksumResponse, 300))
        .toString('utf8')
        .trim()
        .split(/\s/)[0];
      const head = await transport.fetch(url, { method: 'HEAD' });
      if (!head.ok) throw new Error('Biblioteca Fabric indisponível.');
      metadata = { ...library, size: Number(head.headers.get('content-length')), sha1: checksum };
    }
    const path = 'libraries/' + relative;
    add(path, { ...metadata, url }, metadata.sha256 ? 'sha256' : 'sha1');
    classPath.push(path);
  }
  classPath.push(clientPath);
  const assets = await checkedJson(
    vanilla.assetIndex.url,
    hash(vanilla.assetIndex.sha1, 'sha1'),
    integer(vanilla.assetIndex.size),
    transport,
  );
  const assetObjects = Object.values(assets.objects ?? {}) as any[];
  if (assetObjects.length > 100000) throw new Error('Índice de assets grande demais.');
  const uniqueAssets = new Map<string, any>();
  for (const object of assetObjects) {
    hash(object.hash, 'sha1');
    integer(object.size);
    uniqueAssets.set(object.hash, object);
  }
  for (const object of uniqueAssets.values())
    add(`assets/objects/${object.hash.slice(0, 2)}/${object.hash}`, {
      url: `https://resources.download.minecraft.net/${object.hash.slice(0, 2)}/${object.hash}`,
      size: object.size,
      sha1: object.hash,
    });
  const javaResponse = (await transport.json(
    'https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse',
  )) as any[];
  const java = javaResponse[0]?.binary?.package;
  if (
    !java ||
    !java.name?.endsWith('.zip') ||
    javaResponse[0]?.version?.major !== 21 ||
    javaResponse[0]?.binary?.os !== 'windows' ||
    javaResponse[0]?.binary?.architecture !== 'x64'
  )
    throw new Error('Java 21 para Windows indisponível.');
  const javaFile = {
    url: java.link,
    size: integer(java.size),
    hash: hash(java.checksum, 'sha256'),
  };
  return {
    minecraftVersion,
    fabricVersion,
    versionId: fabric.id,
    vanilla,
    fabric,
    files,
    classPath,
    natives,
    assetIndexId: vanilla.assetIndex.id,
    java: javaFile,
    estimatedBytes: files.reduce((n, f) => n + f.size, 0) + javaFile.size + 400 * 1024 ** 2,
  };
}
export async function installGame(
  root: string,
  plan: GamePlan,
  signal: AbortSignal,
  onProgress: (completed: number, total: number, label: string) => void,
): Promise<string> {
  await ownedPath(root, 'installation-check');
  onProgress(0, plan.files.length + 3, 'Conferindo arquivos existentes e espaço disponível…');
  const missing = await missingDownloadBytes(root, [
    ...plan.files,
    {
      path: `runtime/java-${plan.java.hash}.zip`,
      url: plan.java.url,
      size: plan.java.size,
      hash: plan.java.hash,
      algorithm: 'sha256',
    },
  ]);
  signal.throwIfAborted();
  const disk = await statfs(root);
  if (Number(disk.bavail) * Number(disk.bsize) < missing + 400 * 1024 ** 2 + 1024 ** 3)
    throw new Error('Espaço insuficiente. Libere pelo menos 3 GB para a instalação Atlas.');
  const transport = new TrustedTransport(GAME_ORIGINS);
  let completed = 0;
  const total = plan.files.length + 3;
  // Small bounded pool keeps assets efficient without starting thousands of requests at once.
  const group = new AbortController();
  const transferSignal = AbortSignal.any([signal, group.signal]);
  let cursor = 0;
  const results = await Promise.allSettled(
    Array.from({ length: 6 }, async () => {
      try {
        while (cursor < plan.files.length) {
          transferSignal.throwIfAborted();
          const file = plan.files[cursor++];
          await downloadFile(root, file, transport, transferSignal);
          onProgress(++completed, total, file.path);
        }
      } catch (error) {
        group.abort();
        throw error;
      }
    }),
  );
  const failure = results.find((result) => result.status === 'rejected');
  if (failure?.status === 'rejected') throw failure.reason;

  const indexPath = await ownedPath(root, `assets/indexes/${plan.assetIndexId}.json`);
  await mkdir(dirname(indexPath), { recursive: true });
  const indexResponse = await transport.fetch(plan.vanilla.assetIndex.url);
  const indexBytes = await limitedBytes(indexResponse, plan.vanilla.assetIndex.size);
  if (createHash('sha1').update(indexBytes).digest('hex') !== plan.vanilla.assetIndex.sha1)
    throw new Error('Índice de assets corrompido.');
  await writeFile(indexPath, indexBytes, { mode: 0o600 });
  await downloadFile(
    root,
    {
      path: `runtime/java-${plan.java.hash}.zip`,
      url: plan.java.url,
      size: plan.java.size,
      hash: plan.java.hash,
      algorithm: 'sha256',
    },
    transport,
    signal,
  );
  onProgress(++completed, total, 'Java 21');
  const javaDirectory = `runtime/java-${plan.java.hash}`;
  const javaRoot = await ownedPath(root, javaDirectory);
  const marker = join(javaRoot, 'atlas-runtime-complete.json');
  const staging = javaRoot + '.staging';
  await rm(staging, { recursive: true, force: true });
  signal.throwIfAborted();
  await extractArchive(join(root, `runtime/java-${plan.java.hash}.zip`), staging, signal);
  const directories = await readdir(staging);
  if (directories.length !== 1) throw new Error('Estrutura Java inválida.');
  const relative = directories[0] + '/bin/javaw.exe';
  await stat(await ownedPath(staging, relative));
  await writeFile(
    join(staging, 'atlas-runtime-complete.json'),
    JSON.stringify({ path: relative }),
    { mode: 0o600 },
  );
  await rm(javaRoot, { recursive: true, force: true });
  await rename(staging, javaRoot);

  const nativeRoot = await ownedPath(root, `natives/${plan.versionId}`);
  if (plan.natives.length) {
    await rm(nativeRoot, { recursive: true, force: true });
    await mkdir(nativeRoot, { recursive: true });
    for (const path of plan.natives)
      await extractArchive(join(root, path), nativeRoot, signal, (p) =>
        p.toLowerCase().endsWith('.dll'),
      );
  }
  onProgress(++completed, total, 'Bibliotecas nativas');
  const saved = JSON.parse(await readFile(marker, 'utf8'));
  await writeFile(
    await ownedPath(root, 'game-profile.json'),
    JSON.stringify({ plan, javaPath: javaDirectory + '/' + saved.path }),
    { mode: 0o600 },
  );
  onProgress(total, total, 'Minecraft e Fabric prontos');
  return javaDirectory + '/' + saved.path;
}
export function expandArguments(values: any[], variables: Record<string, string>): string[] {
  const result: string[] = [];
  for (const entry of values) {
    if (typeof entry === 'string') result.push(entry);
    else if (rulesAllow(entry.rules)) {
      if (Array.isArray(entry.value)) result.push(...entry.value);
      else result.push(entry.value);
    }
  }
  return result.map((arg) => {
    if (typeof arg !== 'string' || arg.includes('\0'))
      throw new Error('Argumento Minecraft inválido.');
    return arg.replace(/\$\{([^}]+)\}/g, (_, key) => {
      if (!(key in variables)) throw new Error('Argumento Minecraft desconhecido: ' + key);
      return variables[key];
    });
  });
}
