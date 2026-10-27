import { open, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { StringDecoder } from 'node:string_decoder';
export function redactLog(value: string, secrets: readonly string[]): string {
  let result = value;
  for (const secret of secrets.filter(Boolean))
    for (const encoded of [secret, encodeURIComponent(secret)])
      result = result.split(encoded).join('[REDACTED]');
  return result.replace(
    /((?:access_token|refresh_token|id_token|authorization)["']?\s*[:=]\s*["']?)(?:Bearer\s+)?[^\s"',}]+/gi,
    '$1[REDACTED]',
  );
}
export async function createGameLog(directory: string, secrets: readonly string[]) {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, 'game-' + Date.now() + '.log');
  const handle = await open(path, 'wx', 0o600);
  let queue: Promise<void> = Promise.resolve();
  let written = 0;
  const decoders = [new StringDecoder('utf8'), new StringDecoder('utf8')];
  const pending = ['', ''];
  const omitted = [false, false];
  const line = (value: string) => {
    const safe = redactLog(value, secrets) + '\n';
    if ((written += Buffer.byteLength(safe)) > 10 * 1024 ** 2) return;
    queue = queue
      .then(async () => {
        await handle.writeFile(safe);
      })
      .catch(() => {});
  };
  return {
    path,
    append(chunk: Buffer, source: 0 | 1) {
      pending[source] += decoders[source].write(chunk);
      while (pending[source].includes('\n')) {
        const index = pending[source].indexOf('\n');
        const value = pending[source].slice(0, index);
        pending[source] = pending[source].slice(index + 1);
        if (!omitted[source]) line(value);
        omitted[source] = false;
      }
      if (pending[source].length > 65536) {
        pending[source] = '';
        omitted[source] = true;
        line('[Linha longa omitida do diagnóstico]');
      }
    },
    async close() {
      for (const source of [0, 1] as const) {
        pending[source] += decoders[source].end();
        if (pending[source] && !omitted[source]) line(pending[source]);
      }
      await queue;
      await handle.close();
    },
  };
}
