import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync, sign } from 'node:crypto';
import { verifyLauncherRelease, LAUNCHER_FEED } from '../src/main/launcher/updates';
const keys = generateKeyPairSync('ed25519'),
  key = keys.publicKey.export({ type: 'spki', format: 'pem' }).toString();
const base = {
  schemaVersion: 1,
  version: '0.6.0',
  platform: 'win32-x64',
  filename: 'Atlas-Launcher-0.6.0-Windows-x64.zip',
  size: 4,
  sha256: 'a'.repeat(64),
  parts: [{ path: 'launcher/files/0.6.0/000.bin', size: 4, sha256: 'b'.repeat(64) }],
};
function signed(value: unknown) {
  const bytes = Buffer.from(JSON.stringify(value));
  return JSON.stringify({
    keyId: 'atlas-release-2026',
    payload: bytes.toString('base64'),
    signature: sign(null, bytes, keys.privateKey).toString('base64'),
  });
}
test('launcher feed is on official Atlas site and accepts authentic bounded packages', () => {
  assert.equal(LAUNCHER_FEED, 'https://www.atlascobblemon.com.br/launcher/windows/latest.json');
  assert.deepEqual(verifyLauncherRelease(signed(base), key), base);
});
test('launcher packages reject tampering, oversized parts, external paths and invalid totals', () => {
  for (const value of [
    { ...base, size: 5 },
    { ...base, filename: '../evil.exe' },
    { ...base, parts: [{ ...base.parts[0], path: 'https://attacker.invalid/x' }] },
    { ...base, parts: [{ ...base.parts[0], path: 'launcher/files/../evil' }] },
    { ...base, size: 21 * 1024 ** 2, parts: [{ ...base.parts[0], size: 21 * 1024 ** 2 }] },
    { ...base, platform: 'linux' },
    { ...base, parts: [base.parts[0], base.parts[0]] },
  ])
    assert.throws(() => verifyLauncherRelease(signed(value), key));
  const envelope = JSON.parse(signed(base));
  envelope.payload = Buffer.from('{}').toString('base64');
  assert.throws(() => verifyLauncherRelease(JSON.stringify(envelope), key));
});

test('launcher download assembles verified parts and refuses a corrupt final package', async () => {
  const { LauncherUpdates } = await import('../src/main/launcher/updates');
  const { mkdtemp, readFile, rm } = await import('node:fs/promises');
  const { join } = await import('node:path');
  const { tmpdir } = await import('node:os');
  const { createHash } = await import('node:crypto');
  const data = Buffer.from('synthetic zip fixture'),
    sha = (x: Buffer) => createHash('sha256').update(x).digest('hex');
  const root = await mkdtemp(join(tmpdir(), 'atlas-launcher-update-'));
  const original = globalThis.fetch;
  try {
    let feed = signed({
      ...base,
      size: data.length,
      sha256: sha(data),
      parts: [{ path: 'launcher/files/0.6.0/000.bin', size: data.length, sha256: sha(data) }],
    });
    globalThis.fetch = async (input) =>
      new Response(String(input).endsWith('/latest.json') ? feed : data);
    const updater = new LauncherUpdates(root, key, '0.5.0');
    await updater.check();
    assert.equal(updater.state.status, 'available');
    await updater.download();
    assert.equal(updater.state.status, 'downloaded');
    assert.deepEqual(await readFile(join(root, base.filename)), data);
    await rm(join(root, base.filename));
    feed = signed({
      ...base,
      size: data.length,
      sha256: '0'.repeat(64),
      parts: [{ path: 'launcher/files/0.6.0/000.bin', size: data.length, sha256: sha(data) }],
    });
    const corrupt = new LauncherUpdates(root, key, '0.5.0');
    await corrupt.check();
    await corrupt.download();
    assert.equal(corrupt.state.status, 'error');
    await assert.rejects(readFile(join(root, base.filename)));
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});

test('automatic updates accept only signed installers and recheck the executable before applying', async () => {
  const { LauncherUpdates } = await import('../src/main/launcher/updates');
  const { mkdtemp, readFile, writeFile, rm } = await import('node:fs/promises');
  const { join } = await import('node:path');
  const { tmpdir } = await import('node:os');
  const { createHash } = await import('node:crypto');
  const data = Buffer.from('synthetic installer fixture');
  const digest = createHash('sha256').update(data).digest('hex');
  const release = {
    ...base,
    schemaVersion: 2,
    filename: 'Atlas-Launcher-0.6.0-Setup-x64.exe',
    size: data.length,
    sha256: digest,
    parts: [{ path: 'launcher/files/0.6.0/000.bin', size: data.length, sha256: digest }],
  };
  assert.deepEqual(verifyLauncherRelease(signed(release), key), release);
  assert.throws(() => verifyLauncherRelease(signed({ ...release, schemaVersion: 1 }), key));
  const root = await mkdtemp(join(tmpdir(), 'atlas-auto-'));
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (input) =>
      new Response(String(input).endsWith('/latest.json') ? signed(release) : data);
    const updater = new LauncherUpdates(root, key, '0.5.0');
    updater.configureAutomatic(true);
    await updater.check();
    assert.equal(updater.state.status, 'downloaded');
    const path = await updater.preparedInstaller();
    assert.equal(path, join(root, release.filename));
    assert.deepEqual(await readFile(path!), data);
    await writeFile(path!, 'tampered');
    await assert.rejects(updater.preparedInstaller());
  } finally {
    globalThis.fetch = original;
    await rm(root, { recursive: true, force: true });
  }
});
