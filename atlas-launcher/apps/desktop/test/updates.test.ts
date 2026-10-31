import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { generateKeyPairSync, sign } from 'node:crypto';
import { selectRelease, fetchRelease, RELEASE_FEED } from '../src/main/modpack/updates';
const keys = generateKeyPairSync('ed25519');
const trust = {
  publicKeys: { fixture: keys.publicKey.export({ type: 'spki', format: 'pem' }).toString() },
  downloadOrigins: new Set(['https://fixture.invalid']),
};
const base = {
  schemaVersion: 1,
  packId: 'atlas-cobblemon',
  version: '1.0.0',
  channel: 'beta',
  minecraftVersion: '1.21.1',
  modLoader: { type: 'fabric', version: '0.18.0' },
  minimumLauncherVersion: '0.4.0',
  minimumCompatibleVersion: '1.0.0',
  publishedAt: '2026-10-28T00:00:00Z',
  releaseNotes: 'Synthetic test',
  files: [
    {
      path: 'mods/fixture.jar',
      url: 'https://fixture.invalid/fixture.jar',
      size: 1,
      sha256: 'a'.repeat(64),
    },
  ],
  removals: [],
};
function envelope(change: object = {}) {
  const bytes = Buffer.from(JSON.stringify({ ...base, ...change }));
  return JSON.stringify({
    keyId: 'fixture',
    payload: bytes.toString('base64'),
    signature: sign(null, bytes, keys.privateKey).toString('base64'),
  });
}
test('updates accept only newer signed releases and preserve identical version', () => {
  const current = envelope();
  const next = envelope({ version: '1.1.0' });
  assert.equal(selectRelease(current, next, trust, '0.5.0'), next);
  assert.equal(selectRelease(current, current, trust, '0.5.0'), current);
});
test('updates reject downgrade, changed same-version content, channel and launcher incompatibility', () => {
  const current = envelope();
  for (const change of [
    { version: '0.9.0' },
    { releaseNotes: 'Changed' },
    { channel: 'stable' },
    { minimumLauncherVersion: '9.0.0' },
  ])
    assert.throws(() => selectRelease(current, envelope(change), trust, '0.5.0'));
  const tampered = JSON.parse(envelope({ version: '1.1.0' }));
  tampered.signature = 'A'.repeat(88);
  assert.throws(() => selectRelease(current, JSON.stringify(tampered), trust, '0.5.0'));
});
test('remote feed handles failure, bounded payload and rejects external redirect', async () => {
  await assert.rejects(fetchRelease(async () => new Response('', { status: 404 })));
  await assert.rejects(fetchRelease(async () => new Response('x'.repeat(2 * 1024 * 1024 + 1))));
  await assert.rejects(
    fetchRelease(
      async () =>
        new Response('', { status: 302, headers: { location: 'https://attacker.invalid/feed' } }),
    ),
  );
  let visited = '';
  assert.equal(
    await fetchRelease(async (input) => {
      visited = String(input);
      return new Response('signed envelope fixture');
    }),
    'signed envelope fixture',
  );
  assert.equal(visited, RELEASE_FEED);
});
