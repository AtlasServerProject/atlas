import { Transform } from 'node:stream';
import { crc32 } from 'node:zlib';
import { open as openZip, type ZipFile, type Entry } from 'yauzl';
import { createWriteStream } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { pipeline } from 'node:stream/promises';
import { ownedPath, safeRelative } from './paths';
export async function extractArchive(
  archive: string,
  root: string,
  signal: AbortSignal,
  select: (path: string) => boolean = () => true,
): Promise<void> {
  const zip = await new Promise<ZipFile>((resolve, reject) =>
    openZip(
      archive,
      { lazyEntries: true, autoClose: true, validateEntrySizes: true },
      (error, value) => (error || !value ? reject(error) : resolve(value)),
    ),
  );
  await new Promise<void>((resolve, reject) => {
    let count = 0,
      total = 0;
    const seen = new Set<string>();
    let stopped = false;
    const fail = (error: unknown) => {
      if (stopped) return;
      stopped = true;
      signal.removeEventListener('abort', abort);
      zip.close();
      reject(error);
    };
    const abort = () => fail(new Error('Instalação cancelada.'));
    signal.addEventListener('abort', abort, { once: true });
    zip.on('error', fail);
    zip.on('end', () => {
      if (!stopped) {
        stopped = true;
        signal.removeEventListener('abort', abort);
        resolve();
      }
    });
    zip.on('entry', (entry: Entry) => {
      void (async () => {
        signal.throwIfAborted();
        if (++count > 30000 || (total += entry.uncompressedSize) > 1024 ** 3)
          throw new Error('Arquivo compactado excede os limites.');
        const name = entry.fileName.endsWith('/') ? entry.fileName.slice(0, -1) : entry.fileName;
        safeRelative(name);
        if (((entry.externalFileAttributes >>> 16) & 0xf000) === 0xa000)
          throw new Error('Link em arquivo compactado não permitido.');
        if (!select(name)) {
          zip.readEntry();
          return;
        }
        const key = name.toLowerCase();
        if (seen.has(key)) throw new Error('Arquivo compactado tem nomes duplicados.');
        seen.add(key);
        const target = await ownedPath(root, name);
        if (entry.fileName.endsWith('/')) await mkdir(target, { recursive: true });
        else {
          await mkdir(dirname(target), { recursive: true });
          const stream = await new Promise<NodeJS.ReadableStream>((resolve, reject) =>
            zip.openReadStream(entry, (e, s) => (e || !s ? reject(e) : resolve(s))),
          );
          await pipeline(stream, createWriteStream(target, { flags: 'wx', mode: 0o600 }), {
            signal,
          });
        }
        zip.readEntry();
      })().catch(fail);
    });
    zip.readEntry();
  });
}
