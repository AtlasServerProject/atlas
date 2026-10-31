import { test } from 'node:test';
import assert from 'node:assert/strict';
import { offlineProfile } from '../src/main/auth/offline';
import { MicrosoftLogin } from '../src/main/auth/microsoft';
import { TokenVault } from '../src/main/auth/vault';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
test('offline nickname uses Java-compatible UUID and rejects malformed names', () => {
  assert.deepEqual(offlineProfile('Notch'), {
    id: 'b50ad385829d3141a2167e7d7539ba7f',
    name: 'Notch',
    kind: 'offline',
  });
  assert.notEqual(offlineProfile('Notch').id, offlineProfile('notch').id);
  for (const name of [
    '',
    'ab',
    'x'.repeat(17),
    'hello world',
    '../Admin',
    'ábc',
    'a\nb',
    '--name',
    null,
    {},
  ])
    assert.throws(() => offlineProfile(name));
});
test('offline session needs no Microsoft app, never claims Microsoft identity and logout revokes it', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-offline-'));
  try {
    const auth = new MicrosoftLogin(
      null,
      new TokenVault(join(root, 'cache'), {
        available: () => false,
        encrypt: () => {
          throw Error('unused');
        },
        decrypt: () => {
          throw Error('unused');
        },
      }),
    );
    await auth.signInOffline('Trainer_1');
    const session = await auth.forGame();
    assert.equal(auth.publicState().configured, false);
    assert.equal(auth.publicState().status, 'signed-in');
    assert.equal(session.profile.kind, 'offline');
    assert.equal(session.accessToken, '0');
    assert.equal(session.xuid, '');
    assert.equal('accessToken' in auth.publicState(), false);
    await assert.rejects(auth.signInOffline('bad name'));
    assert.equal(auth.publicState().account?.name, 'Trainer_1');
    await auth.signOut();
    assert.equal(auth.publicState().status, 'signed-out');
    await assert.rejects(auth.forGame());
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
