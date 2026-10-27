import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { mkdir, open, readFile, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { ownedPath } from './paths';
export interface DownloadFile {
  path: string;
  url: string;
  size: number;
  hash: string;
  algorithm: 'sha1' | 'sha256';
}
export async function fileMatches(
  path: string,
  file: Pick<DownloadFile, 'size' | 'hash' | 'algorithm'>,
): Promise<boolean> {
  try {
    if ((await stat(path)).size !== file.size) return false;
    const hash = createHash(file.algorithm);
    for await (const chunk of createReadStream(path)) hash.update(chunk);
    return hash.digest('hex') === file.hash;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}
export class TrustedTransport {
  constructor(
    readonly origins: ReadonlySet<string>,
    private request: typeof fetch = fetch,
    private baseSignal?: AbortSignal,
  ) {}
  async fetch(url: string, init: RequestInit = {}): Promise<Response> {
    let current = url;
    for (let i = 0; i < 6; i++) {
      const parsed = new URL(current);
      if (
        parsed.protocol !== 'https:' ||
        parsed.username ||
        parsed.password ||
        !this.origins.has(parsed.origin)
      )
        throw new Error('Origem de download não autorizada.');
      const response = await this.request(parsed.href, {
        ...init,
        redirect: 'manual',
        signal: AbortSignal.any([
          ...(init.signal ? [init.signal] : []),
          ...(this.baseSignal ? [this.baseSignal] : []),
          AbortSignal.timeout(120000),
        ]),
      });
      if ([301, 302, 303, 307, 308].includes(response.status)) {
        const location = response.headers.get('location');
        await response.body?.cancel();
        if (!location) throw new Error('Redirecionamento inválido.');
        current = new URL(location, parsed).href;
        continue;
      }
      return response;
    }
    throw new Error('Redirecionamentos demais.');
  }
  async json(url: string, max = 5 * 1024 * 1024): Promise<unknown> {
    const response = await this.fetch(url);
    if (!response.ok) throw new Error('Não foi possível consultar os arquivos oficiais.');
    const buffer = await limitedBytes(response, max);
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer));
  }
}
export async function limitedBytes(response: Response, max: number): Promise<Uint8Array> {
  if (!response.body) throw new Error('Resposta vazia.');
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const result = await reader.read();
      if (result.done) break;
      size += result.value.length;
      if (size > max) throw new Error('Resposta excede o tamanho permitido.');
      chunks.push(result.value);
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
  return Buffer.concat(chunks, size);
}
export async function downloadFile(
  root: string,
  file: DownloadFile,
  transport: TrustedTransport,
  signal: AbortSignal,
  onBytes: (received: number) => void = () => {},
): Promise<void> {
  if (
    !Number.isSafeInteger(file.size) ||
    file.size <= 0 ||
    file.size > 2 * 1024 ** 3 ||
    !(file.algorithm === 'sha256' ? /^[a-f0-9]{64}$/ : /^[a-f0-9]{40}$/).test(file.hash)
  )
    throw new Error('Metadados de download inválidos.');
  const target = await ownedPath(root, file.path);
  if (await fileMatches(target, file)) {
    onBytes(file.size);
    return;
  }
  const part = await ownedPath(root, file.path + '.part');
  const meta = await ownedPath(root, file.path + '.part.json');
  if (await fileMatches(part, file)) {
    await rename(part, target);
    await unlink(meta).catch(() => {});
    onBytes(file.size);
    return;
  }
  await mkdir(dirname(target), { recursive: true });
  let offset = 0;
  let etag = '';
  try {
    const saved = JSON.parse(await readFile(meta, 'utf8'));
    const size = (await stat(part)).size;
    if (
      saved.url === file.url &&
      saved.hash === file.hash &&
      typeof saved.etag === 'string' &&
      /^"[^"\r\n]+"$/.test(saved.etag) &&
      size > 0 &&
      size < file.size
    ) {
      offset = size;
      etag = saved.etag;
    }
  } catch {}
  const headers: Record<string, string> = { 'Accept-Encoding': 'identity' };
  if (offset) {
    headers.Range = `bytes=${offset}-`;
    headers['If-Range'] = etag;
  }
  const response = await transport.fetch(file.url, {
    headers,
    signal: AbortSignal.any([signal, AbortSignal.timeout(300000)]),
  });
  if (!response.ok || !response.body)
    throw new Error('Falha ao baixar arquivo oficial. Tente novamente.');
  if (offset && response.status === 206) {
    if (
      response.headers.get('content-range') !== `bytes ${offset}-${file.size - 1}/${file.size}` ||
      response.headers.get('etag') !== etag
    ) {
      await response.body.cancel();
      await unlink(meta).catch(() => {});
      throw new Error('O arquivo mudou durante o download. Tente novamente.');
    }
  } else {
    if (response.status !== 200) {
      await response.body.cancel();
      throw new Error('Resposta parcial inválida.');
    }
    offset = 0;
  }
  const declared = response.headers.get('content-length');
  if (declared && Number(declared) !== file.size - offset) {
    await response.body.cancel();
    throw new Error('Tamanho de download divergente.');
  }
  const responseTag = response.headers.get('etag') ?? '';
  await writeFile(meta, JSON.stringify({ url: file.url, hash: file.hash, etag: responseTag }), {
    mode: 0o600,
  });
  const handle = await open(part, offset ? 'a' : 'w', 0o600);
  let received = offset;
  const reader = response.body.getReader();
  try {
    onBytes(received);
    while (true) {
      signal.throwIfAborted();
      const result = await reader.read();
      if (result.done) break;
      received += result.value.byteLength;
      if (received > file.size) throw new Error('Arquivo excede o tamanho esperado.');
      let written = 0;
      while (written < result.value.length) {
        const resultWrite = await handle.write(result.value.subarray(written));
        if (!resultWrite.bytesWritten) throw new Error('Falha de gravação.');
        written += resultWrite.bytesWritten;
      }
      onBytes(received);
    }
    await handle.sync();
  } finally {
    await handle.close();
    await reader.cancel().catch(() => {});
  }
  if (!(await fileMatches(part, file))) {
    await unlink(part).catch(() => {});
    await unlink(meta).catch(() => {});
    throw new Error('Arquivo corrompido: a integridade não confere.');
  }
  await rename(part, target);
  await unlink(meta).catch(() => {});
}

export async function missingDownloadBytes(
  root: string,
  files: readonly DownloadFile[],
): Promise<number> {
  let bytes = 0;
  let cursor = 0;
  await Promise.all(
    Array.from({ length: 4 }, async () => {
      while (cursor < files.length) {
        const file = files[cursor++];
        if (!(await fileMatches(await ownedPath(root, file.path), file))) bytes += file.size;
      }
    }),
  );
  return bytes;
}
