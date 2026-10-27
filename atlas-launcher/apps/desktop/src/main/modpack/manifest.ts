import { createPublicKey, verify } from 'node:crypto';
export interface ManagedFile {
  path: string;
  url: string;
  size: number;
  sha256: string;
}
export interface Manifest {
  schemaVersion: 1;
  packId: 'atlas-cobblemon';
  version: string;
  channel: 'stable' | 'beta';
  minecraftVersion: string;
  modLoader: { type: 'fabric'; version: string };
  minimumLauncherVersion: string;
  minimumCompatibleVersion: string;
  publishedAt: string;
  releaseNotes: string;
  files: ManagedFile[];
  removals: string[];
}
export interface ManifestTrust {
  publicKeys: Readonly<Record<string, string>>;
  downloadOrigins: ReadonlySet<string>;
  bundledFiles?: ReadonlySet<string>;
}
const MAX_BYTES = 2 * 1024 * 1024;
const roots = new Set(['mods', 'config', 'resourcepacks', 'shaderpacks']);
const version = /^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/;
function object(value: unknown, keys: string[]): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Objeto inválido.');
  const data = value as Record<string, unknown>;
  if (Object.keys(data).length !== keys.length || Object.keys(data).some((k) => !keys.includes(k)))
    throw new Error('Campos inválidos.');
  return data;
}
function text(value: unknown, max = 200): string {
  if (typeof value !== 'string' || !value || value.length > max) throw new Error('Texto inválido.');
  return value;
}
export function validateManagedPath(value: unknown): string {
  const path = text(value, 240);
  const parts = path.split('/');
  if (
    parts.length < 2 ||
    !roots.has(parts[0]) ||
    parts.some(
      (p) =>
        !p ||
        p === '.' ||
        p === '..' ||
        /[\\:%\x00-\x1f<>"|?*]/.test(p) ||
        /[. ]$/.test(p) ||
        /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(p),
    )
  )
    throw new Error('Caminho não autorizado.');
  return path;
}
export function parseManifest(
  value: unknown,
  origins: ReadonlySet<string>,
  bundledFiles: ReadonlySet<string> = new Set(),
): Manifest {
  const data = object(value, [
    'schemaVersion',
    'packId',
    'version',
    'channel',
    'minecraftVersion',
    'modLoader',
    'minimumLauncherVersion',
    'minimumCompatibleVersion',
    'publishedAt',
    'releaseNotes',
    'files',
    'removals',
  ]);
  if (
    data.schemaVersion !== 1 ||
    data.packId !== 'atlas-cobblemon' ||
    !['stable', 'beta'].includes(String(data.channel))
  )
    throw new Error('Manifesto incompatível.');
  for (const k of ['version', 'minimumLauncherVersion', 'minimumCompatibleVersion'])
    if (!version.test(text(data[k]))) throw new Error('Versão inválida.');
  if (!/^\d+\.\d+(?:\.\d+)?$/.test(text(data.minecraftVersion)))
    throw new Error('Minecraft inválido.');
  const loader = object(data.modLoader, ['type', 'version']);
  if (loader.type !== 'fabric' || !version.test(text(loader.version)))
    throw new Error('Loader inválido.');
  if (
    !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(text(data.publishedAt)) ||
    !Number.isFinite(Date.parse(data.publishedAt as string))
  )
    throw new Error('Data inválida.');
  if (typeof data.releaseNotes !== 'string' || data.releaseNotes.length > 20000)
    throw new Error('Notas inválidas.');
  if (
    !Array.isArray(data.files) ||
    !data.files.length ||
    data.files.length > 10000 ||
    !Array.isArray(data.removals) ||
    data.removals.length > 10000
  )
    throw new Error('Lista de arquivos inválida.');
  const files: ManagedFile[] = data.files.map((value) => {
    const file = object(value, ['path', 'url', 'size', 'sha256']);
    const path = validateManagedPath(file.path);
    const url = new URL(text(file.url, 4096));
    if (
      !(
        url.protocol === 'https:' ||
        (url.protocol === 'atlas-bundled:' &&
          !url.hostname &&
          bundledFiles.has(url.pathname.slice(1)))
      ) ||
      url.username ||
      url.password ||
      url.hash ||
      (url.protocol === 'https:' && !origins.has(url.origin))
    )
      throw new Error('Origem de download não autorizada.');
    if (
      typeof file.size !== 'number' ||
      !Number.isSafeInteger(file.size) ||
      file.size <= 0 ||
      file.size > 2 * 1024 ** 3
    )
      throw new Error('Tamanho inválido.');
    if (!/^[a-f0-9]{64}$/.test(text(file.sha256))) throw new Error('Hash inválido.');
    return { path, url: url.href, size: file.size, sha256: file.sha256 as string };
  });
  const removals = data.removals.map(validateManagedPath);
  const paths = [...files.map((f) => f.path), ...removals].map((p) => p.toLowerCase());
  const unique = new Set(paths);
  if (unique.size !== paths.length) throw new Error('Caminhos duplicados.');
  for (const path of paths) {
    const segments = path.split('/');
    for (let i = 1; i < segments.length; i++)
      if (unique.has(segments.slice(0, i).join('/')))
        throw new Error('Arquivo usado como diretório.');
  }
  return { ...data, files, removals, modLoader: loader } as unknown as Manifest;
}
function base64(value: unknown, max: number): Buffer {
  const input = text(value, max);
  if (input.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(input))
    throw new Error('Base64 inválido.');
  const decoded = Buffer.from(input, 'base64');
  if (decoded.toString('base64') !== input) throw new Error('Base64 não canônico.');
  return decoded;
}
export function verifyManifestEnvelope(serialized: string, trust: ManifestTrust): Manifest {
  if (Buffer.byteLength(serialized, 'utf8') > MAX_BYTES * 2)
    throw new Error('Envelope muito grande.');
  const envelope = object(JSON.parse(serialized), ['keyId', 'payload', 'signature']);
  const keyId = text(envelope.keyId, 100);
  if (!Object.hasOwn(trust.publicKeys, keyId)) throw new Error('Chave não confiável.');
  const payload = base64(envelope.payload, Math.ceil(MAX_BYTES / 3) * 4);
  const signature = base64(envelope.signature, 88);
  const key = createPublicKey(trust.publicKeys[keyId]);
  if (
    key.asymmetricKeyType !== 'ed25519' ||
    signature.length !== 64 ||
    !verify(null, payload, key, signature)
  )
    throw new Error('Assinatura inválida.');
  const decoded = new TextDecoder('utf-8', { fatal: true }).decode(payload);
  const parsed: unknown = JSON.parse(decoded);
  if (JSON.stringify(parsed) !== decoded) throw new Error('Payload JSON não canônico.');
  return parseManifest(parsed, trust.downloadOrigins, trust.bundledFiles);
}
