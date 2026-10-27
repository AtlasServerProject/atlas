import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import {
  parseManifest,
  validateManagedPath,
  verifyManifestEnvelope,
} from '../src/main/modpack/manifest';
import { planFiles, verifyFileBytes } from '../src/main/modpack/integrity';
// Synthetic, test-only fixture. Never bundled or exposed as an official Atlas release.
const bytes = Buffer.from('fixture');
const hash = createHash('sha256').update(bytes).digest('hex');
const file = {
  path: 'mods/test.jar',
  url: 'https://fixture.invalid/test.jar',
  size: bytes.length,
  sha256: hash,
};
const manifest = () => ({
  schemaVersion: 1,
  packId: 'atlas-cobblemon',
  version: '1.0.0',
  channel: 'stable',
  minecraftVersion: '1.21.1',
  modLoader: { type: 'fabric', version: '0.1.0' },
  minimumLauncherVersion: '0.3.0',
  minimumCompatibleVersion: '1.0.0',
  publishedAt: '2026-10-27T00:00:00Z',
  releaseNotes: 'Test fixture',
  files: [file],
  removals: [],
});
const { privateKey, publicKey } = generateKeyPairSync('ed25519');
const trust = {
  publicKeys: { test: publicKey.export({ type: 'spki', format: 'pem' }).toString() },
  downloadOrigins: new Set(['https://fixture.invalid']),
};
function envelope(payload: unknown) {
  const bytes = Buffer.from(JSON.stringify(payload));
  return {
    keyId: 'test',
    payload: bytes.toString('base64'),
    signature: sign(null, bytes, privateKey).toString('base64'),
  };
}
test('aceita assinatura Ed25519 da chave fixada e payload válido', () =>
  assert.equal(
    verifyManifestEnvelope(JSON.stringify(envelope(manifest())), trust).packId,
    'atlas-cobblemon',
  ));
test('rejeita adulteração, assinatura truncada e chave desconhecida', () => {
  for (const change of [
    { payload: Buffer.from('{}').toString('base64') },
    { signature: 'AAAA' },
    { keyId: 'attacker' },
  ])
    assert.throws(() =>
      verifyManifestEnvelope(JSON.stringify({ ...envelope(manifest()), ...change }), trust),
    );
});
test('rejeita schemas, hashes, tamanhos e origens inválidos mesmo assinados', () => {
  for (const invalid of [
    { ...manifest(), schemaVersion: 2 },
    { ...manifest(), extra: 'bad' },
    { ...manifest(), files: [{ ...file, sha256: 'no' }] },
    { ...manifest(), files: [{ ...file, size: -1 }] },
    { ...manifest(), files: [{ ...file, url: 'https://other.invalid/file' }] },
    { ...manifest(), files: [{ ...file, url: 'https://user:pass@fixture.invalid/file' }] },
  ])
    assert.throws(() => verifyManifestEnvelope(JSON.stringify(envelope(invalid)), trust));
});
test('rejeita traversal, drives, ADS, nomes Windows e diretórios pessoais', () => {
  for (const path of [
    '../mods/x.jar',
    '/mods/x.jar',
    'C:/mods/x.jar',
    'mods/../x.jar',
    'mods/a\\b.jar',
    'mods/x:stream',
    'mods/CON.txt',
    'mods/a.',
    'mods/%2e%2e/x',
    'saves/world/file',
    'screenshots/x.png',
    'logs/latest.log',
    'mods//x.jar',
  ])
    assert.throws(() => validateManagedPath(path), path);
  assert.equal(validateManagedPath('config/atlas/settings.json'), 'config/atlas/settings.json');
});
test('rejeita colisões por caixa, remoções conflitantes e arquivo como diretório', () => {
  for (const patch of [
    { files: [file, { ...file, path: 'mods/TEST.jar' }] },
    { removals: ['mods/test.jar'] },
    {
      files: [
        { ...file, path: 'mods/a' },
        { ...file, path: 'mods/a/file' },
      ],
    },
  ])
    assert.throws(() => parseManifest({ ...manifest(), ...patch }, trust.downloadOrigins));
});
test('verifica tamanho e SHA-256 reais dos bytes', () => {
  assert.ok(verifyFileBytes(bytes, file));
  assert.equal(verifyFileBytes(Buffer.from('changed'), file), false);
  assert.equal(verifyFileBytes(bytes, { ...file, size: 1 }), false);
});
test('planeja arquivos ausentes ou modificados sem confiar no número da versão', () => {
  const result = planFiles(
    [file, { ...file, path: 'mods/other.jar' }],
    new Map([['mods/test.jar', { size: file.size, sha256: hash }]]),
  );
  assert.equal(result.unchanged.length, 1);
  assert.equal(result.download[0].path, 'mods/other.jar');
  assert.equal(
    planFiles([file], new Map([['mods/test.jar', { size: file.size, sha256: '0'.repeat(64) }]]))
      .download.length,
    1,
  );
});
test('envelope excessivo e base64 não canônico são rejeitados', () => {
  assert.throws(() => verifyManifestEnvelope(' '.repeat(5 * 1024 ** 2), trust));
  assert.throws(() =>
    verifyManifestEnvelope(JSON.stringify({ ...envelope(manifest()), payload: 'e30' }), trust),
  );
});

test('rejeita conflito de ancestral mesmo com outro caminho entre eles', () => {
  assert.throws(() =>
    parseManifest(
      {
        ...manifest(),
        files: [
          { ...file, path: 'mods/a' },
          { ...file, path: 'mods/a-foo' },
          { ...file, path: 'mods/a/b' },
        ],
      },
      trust.downloadOrigins,
    ),
  );
});
test('rejeita propriedades JSON duplicadas mesmo com assinatura válida', () => {
  const bytes = Buffer.from(
    JSON.stringify(manifest()).replace('"schemaVersion":1', '"schemaVersion":0,"schemaVersion":1'),
  );
  assert.throws(() =>
    verifyManifestEnvelope(
      JSON.stringify({
        keyId: 'test',
        payload: bytes.toString('base64'),
        signature: sign(null, bytes, privateKey).toString('base64'),
      }),
      trust,
    ),
  );
});

import { compareVersions } from '../src/main/modpack/versions';
test('comparação de versões respeita release/pré-release e números', () => {
  assert.ok(compareVersions('0.4.0', '0.3.9') > 0);
  assert.ok(compareVersions('1.0.0', '1.0.0-beta.1') > 0);
  assert.ok(compareVersions('1.0.0-beta.10', '1.0.0-beta.2') > 0);
  assert.equal(compareVersions('1.0.0', '1.0.0'), 0);
  assert.ok(compareVersions('1.0.0-a', '1.0.0-a.1') < 0);
});
