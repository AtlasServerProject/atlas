import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ramLimit, defaultSettings, validateSettings, SettingsStore } from '../src/main/settings';
import { trustedFrame } from '../src/main/origins';
test('RAM reserva 2 GB e limita a 32 GB', () => {
  assert.equal(ramLimit(8 * 1024 ** 3), 6144);
  assert.equal(ramLimit(64 * 1024 ** 3), 32768);
});
test('preferências rejeitam campos arbitrários, frações, booleanos falsos e excesso de RAM', () => {
  const valid = defaultSettings(6144);
  assert.deepEqual(validateSettings(valid, 6144), valid);
  for (const value of [
    { ...valid, token: 'secret' },
    { ...valid, ramMb: 8192 },
    { ...valid, width: 1 },
    { ...valid, height: 720.5 },
    { ...valid, fullscreen: 'false' },
    null,
    [],
  ])
    assert.throws(() => validateSettings(value, 6144));
});
test('origem exata impede sites, query adulterada e subcaminhos', () => {
  const url = 'http://127.0.0.1:5179/';
  assert.ok(trustedFrame(url, url));
  for (const other of [
    'https://evil.invalid/',
    'http://127.0.0.1:5179/other',
    url + '?x=1',
    undefined,
  ])
    assert.equal(trustedFrame(other, url), false);
});
test('preferências persistem atomicamente mesmo com gravações concorrentes', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'atlas-settings-'));
  try {
    const store = new SettingsStore(dir, 6144);
    const initial = await store.read();
    await Promise.all([
      store.save({ ...initial, ramMb: 2048 }),
      store.save({ ...initial, ramMb: 3072 }),
    ]);
    assert.equal((await store.read()).ramMb, 3072);
    const saved = JSON.parse(await readFile(join(dir, 'settings.json'), 'utf8'));
    assert.deepEqual(Object.keys(saved).sort(), Object.keys(initial).sort());
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('RAM insuficiente não permite reservar mais que a capacidade disponível', () => {
  assert.equal(ramLimit(256 * 1048576), 0);
  assert.equal(ramLimit(2048 * 1048576), 0);
  assert.throws(() => validateSettings(defaultSettings(512), 0));
});

import { validateWindowAction } from '../src/main/window-actions';
test('controles de janela aceitam somente ações conhecidas', () => {
  for (const action of ['minimize', 'maximize', 'close'])
    assert.equal(validateWindowAction(action), action);
  for (const action of ['open', {}, null, 42, 'close;exec'])
    assert.throws(() => validateWindowAction(action));
});
