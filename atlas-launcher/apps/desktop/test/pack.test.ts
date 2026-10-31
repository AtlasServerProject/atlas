import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { generateKeyPairSync, sign, createHash } from 'node:crypto';
import { installPack } from '../src/main/installation/pack';
const keys = generateKeyPairSync('ed25519');
const trust = {
  publicKeys: { test: keys.publicKey.export({ type: 'spki', format: 'pem' }).toString() },
  downloadOrigins: new Set(['https://fixture.invalid']),
};
function release(version: string, name: string, data: string, removals: string[] = []) {
  const payload = Buffer.from(
    JSON.stringify({
      schemaVersion: 1,
      packId: 'atlas-cobblemon',
      version,
      channel: 'beta',
      minecraftVersion: '1.21.1',
      modLoader: { type: 'fabric', version: '0.18.0' },
      minimumLauncherVersion: '0.4.0',
      minimumCompatibleVersion: '1.0.0',
      publishedAt: '2026-10-27T00:00:00Z',
      releaseNotes: 'Test only',
      files: [
        {
          path: 'mods/' + name,
          url: 'https://fixture.invalid/' + name,
          size: Buffer.byteLength(data),
          sha256: createHash('sha256').update(data).digest('hex'),
        },
      ],
      removals,
    }),
  );
  return JSON.stringify({
    keyId: 'test',
    payload: payload.toString('base64'),
    signature: sign(null, payload, keys.privateKey).toString('base64'),
  });
}
test('instalação real do pacote faz commit e remove somente arquivos da release anterior', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-pack-'));
  const original = globalThis.fetch;
  try {
    await mkdir(join(root, 'mods'));
    await mkdir(join(root, 'screenshots'));
    await writeFile(join(root, 'mods/personal.jar'), 'personal');
    await writeFile(join(root, 'screenshots/personal.png'), 'personal');
    globalThis.fetch = async () => new Response('first');
    await installPack(
      root,
      release('1.0.0', 'a.jar', 'first'),
      trust,
      root,
      new AbortController().signal,
      () => {},
    );
    assert.equal(await readFile(join(root, 'mods/a.jar'), 'utf8'), 'first');
    globalThis.fetch = async () => new Response('second');
    await installPack(
      root,
      release('1.1.0', 'b.jar', 'second'),
      trust,
      root,
      new AbortController().signal,
      () => {},
    );
    assert.equal(await readFile(join(root, 'mods/b.jar'), 'utf8'), 'second');
    await assert.rejects(readFile(join(root, 'mods/a.jar')));
    assert.equal(await readFile(join(root, 'mods/personal.jar'), 'utf8'), 'personal');
    assert.equal(await readFile(join(root, 'screenshots/personal.png'), 'utf8'), 'personal');
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});
test('cancelamento antes da ativação mantém a release anterior inteira', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-pack-cancel-'));
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('first');
    const first = release('1.0.0', 'a.jar', 'first');
    await installPack(root, first, trust, root, new AbortController().signal, () => {});
    globalThis.fetch = async () => new Response('second');
    const controller = new AbortController();
    await assert.rejects(
      installPack(root, release('1.1.0', 'b.jar', 'second'), trust, root, controller.signal, () =>
        controller.abort(),
      ),
    );
    assert.equal(await readFile(join(root, 'mods/a.jar'), 'utf8'), 'first');
    assert.equal(await readFile(join(root, '.atlas/managed-release.json'), 'utf8'), first);
    await assert.rejects(readFile(join(root, 'mods/b.jar')));
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});

test('launcher antigo não rebaixa uma instalação já atualizada', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-pack-downgrade-'));
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('new');
    await installPack(
      root,
      release('2.0.0', 'a.jar', 'new'),
      trust,
      root,
      new AbortController().signal,
      () => {},
    );
    await assert.rejects(
      installPack(
        root,
        release('1.0.0', 'a.jar', 'old'),
        trust,
        root,
        new AbortController().signal,
        () => {},
      ),
      /antigo/,
    );
    assert.equal(await readFile(join(root, 'mods/a.jar'), 'utf8'), 'new');
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});

test('obsolete removals allow fresh install, skipped releases and repeated repair', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-pack-obsolete-'));
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('first');
    const first = release('1.0.0', 'a.jar', 'first', ['mods/ancient.jar']);
    await installPack(root, first, trust, root, new AbortController().signal, () => {});
    globalThis.fetch = async () => new Response('second');
    const next = release('1.2.0', 'c.jar', 'second', ['mods/a.jar', 'mods/b.jar']);
    await installPack(root, next, trust, root, new AbortController().signal, () => {});
    await installPack(root, next, trust, root, new AbortController().signal, () => {});
    assert.equal(await readFile(join(root, 'mods/c.jar'), 'utf8'), 'second');
    await assert.rejects(readFile(join(root, 'mods/a.jar')));
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});

test('existing unowned removal remains blocked and personal file preserved', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-pack-unowned-'));
  const original = globalThis.fetch;
  try {
    await mkdir(join(root, 'mods'));
    await writeFile(join(root, 'mods/personal.jar'), 'personal');
    globalThis.fetch = async () => new Response('new');
    await assert.rejects(
      installPack(
        root,
        release('1.0.0', 'a.jar', 'new', ['mods/personal.jar']),
        trust,
        root,
        new AbortController().signal,
        () => {},
      ),
      /não gerenciado/,
    );
    assert.equal(await readFile(join(root, 'mods/personal.jar'), 'utf8'), 'personal');
    await assert.rejects(readFile(join(root, '.atlas/managed-release.json')));
    await assert.rejects(readFile(join(root, 'mods/a.jar')));
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});
