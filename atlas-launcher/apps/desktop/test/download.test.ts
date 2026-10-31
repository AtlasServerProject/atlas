import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { downloadFile, TrustedTransport, limitedBytes } from '../src/main/installation/download';
import { ownedPath } from '../src/main/installation/paths';
const data = Buffer.from('abcdef');
const file = {
  path: 'mods/a.jar',
  url: 'https://fixture.invalid/a',
  size: data.length,
  hash: createHash('sha256').update(data).digest('hex'),
  algorithm: 'sha256' as const,
};
const signal = () => new AbortController().signal;
const transport = (fn: (url: any, init: any) => Promise<Response>) =>
  new TrustedTransport(new Set(['https://fixture.invalid']), fn as typeof fetch);
async function temporary(fn: (root: string) => Promise<void>) {
  const root = await mkdtemp(join(tmpdir(), 'atlas-download-'));
  try {
    await fn(root);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
test('download confere hash e reaproveita bytes válidos sem nova requisição', async () =>
  temporary(async (root) => {
    let requests = 0;
    const service = transport(async () => {
      requests++;
      return new Response(data, { headers: { 'Content-Length': '6' } });
    });
    await downloadFile(root, file, service, signal());
    await downloadFile(root, file, service, signal());
    assert.equal(requests, 1);
    assert.deepEqual(await readFile(join(root, file.path)), data);
  }));
test('transferência interrompida retoma somente com ETag e Content-Range corretos', async () =>
  temporary(async (root) => {
    let reads = 0;
    const interrupted = new ReadableStream({
      pull(controller) {
        if (reads++ === 0) controller.enqueue(data.subarray(0, 3));
        else controller.error(new Error('test interruption'));
      },
    });
    await assert.rejects(
      downloadFile(
        root,
        file,
        transport(
          async () =>
            new Response(interrupted, { headers: { ETag: '"v1"', 'Content-Length': '6' } }),
        ),
        signal(),
      ),
    );
    assert.equal((await readFile(join(root, file.path + '.part'))).length, 3);
    await downloadFile(
      root,
      file,
      transport(async (_url, init) => {
        assert.equal(init.headers.Range, 'bytes=3-');
        assert.equal(init.headers['If-Range'], '"v1"');
        return new Response(data.subarray(3), {
          status: 206,
          headers: { ETag: '"v1"', 'Content-Range': 'bytes 3-5/6', 'Content-Length': '3' },
        });
      }),
      signal(),
    );
    assert.deepEqual(await readFile(join(root, file.path)), data);
  }));
test('servidor sem retomada reinicia a transferência sem concatenar dados antigos', async () =>
  temporary(async (root) => {
    await ownedPath(root, file.path);
    await (await import('node:fs/promises')).mkdir(join(root, 'mods'));
    await writeFile(join(root, file.path + '.part'), 'abc');
    await writeFile(
      join(root, file.path + '.part.json'),
      JSON.stringify({ url: file.url, hash: file.hash, etag: '"v1"' }),
    );
    await downloadFile(
      root,
      file,
      transport(async () => new Response(data, { headers: { 'Content-Length': '6' } })),
      signal(),
    );
    assert.deepEqual(await readFile(join(root, file.path)), data);
  }));
test('bytes corrompidos nunca substituem o arquivo anterior', async () =>
  temporary(async (root) => {
    await (await import('node:fs/promises')).mkdir(join(root, 'mods'));
    await writeFile(join(root, file.path), 'old');
    await assert.rejects(
      downloadFile(
        root,
        file,
        transport(async () => new Response('xxxxxx')),
        signal(),
      ),
      /integridade/,
    );
    assert.equal(await readFile(join(root, file.path), 'utf8'), 'old');
  }));
test('redirecionamento para origem externa e respostas excessivas são bloqueados', async () => {
  let count = 0;
  await assert.rejects(
    transport(async () => {
      count++;
      return new Response(null, { status: 302, headers: { Location: 'https://evil.invalid/a' } });
    }).fetch(file.url),
    /Origem/,
  );
  assert.equal(count, 1);
  await assert.rejects(limitedBytes(new Response('123'), 2), /tamanho/);
});
test('caminhos pessoais, traversal e symlinks não escapam do diretório', async () =>
  temporary(async (root) => {
    await assert.rejects(ownedPath(root, '../outside'));
    const outside = await mkdtemp(join(tmpdir(), 'atlas-outside-'));
    try {
      await symlink(outside, join(root, 'mods'), 'dir');
      await assert.rejects(ownedPath(root, 'mods/a.jar'), /Link simbólico/);
    } finally {
      await rm(outside, { recursive: true, force: true });
    }
  }));
test('cancelamento não ativa arquivo parcial', async () =>
  temporary(async (root) => {
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(
      downloadFile(
        root,
        file,
        transport(async () => new Response(data)),
        controller.signal,
      ),
    );
    await assert.rejects(readFile(join(root, file.path)));
  }));
test('arquivo parcial já completo é verificado e ativado sem baixar novamente', async () =>
  temporary(async (root) => {
    await (await import('node:fs/promises')).mkdir(join(root, 'mods'));
    await writeFile(join(root, file.path + '.part'), data);
    await downloadFile(
      root,
      file,
      transport(async () => {
        throw new Error('Network must not be used');
      }),
      signal(),
    );
    assert.deepEqual(await readFile(join(root, file.path)), data);
  }));

test('symlink no ancestral é rejeitado antes de criar diretórios externos', async () =>
  temporary(async (root) => {
    const outside = await mkdtemp(join(tmpdir(), 'atlas-parent-outside-'));
    try {
      await symlink(outside, join(root, 'linked'), 'dir');
      await assert.rejects(
        ownedPath(join(root, 'linked', 'new-root'), 'mods/file.jar'),
        /Link simbólico/,
      );
      await assert.rejects(readFile(join(outside, 'new-root/mods/file.jar')));
    } finally {
      await rm(outside, { recursive: true, force: true });
    }
  }));

import { missingDownloadBytes } from '../src/main/installation/download';
test('preflight de espaço conta somente arquivos ausentes ou corrompidos', async () =>
  temporary(async (root) => {
    await (await import('node:fs/promises')).mkdir(join(root, 'mods'));
    assert.equal(await missingDownloadBytes(root, [file]), 6);
    await writeFile(join(root, file.path), data);
    assert.equal(await missingDownloadBytes(root, [file]), 0);
    await writeFile(join(root, file.path), 'xxxxxx');
    assert.equal(await missingDownloadBytes(root, [file]), 6);
  }));
