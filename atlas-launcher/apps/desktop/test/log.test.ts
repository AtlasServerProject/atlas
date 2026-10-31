import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createGameLog, redactLog } from '../src/main/installation/game-log';
test('diagnóstico redige credenciais, inclusive quando divididas entre chunks', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-log-'));
  try {
    const log = await createGameLog(root, ['PRIVATE_TEST_TOKEN']);
    log.append(Buffer.from('Starting game\nPRIVATE_'), 0);
    log.append(Buffer.from('TEST_TOKEN\naccess_token=another-test-token\n'), 0);
    await log.close();
    const text = await readFile(log.path, 'utf8');
    assert.ok(text.includes('Starting game'));
    assert.equal(text.includes('PRIVATE_TEST_TOKEN'), false);
    assert.equal(text.includes('another-test-token'), false);
    assert.ok(text.includes('[REDACTED]'));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
test('campos comuns de autorização são ocultados sem expor valores', () => {
  assert.equal(redactLog('Authorization: Bearer TOKEN_TEST', []).includes('TOKEN_TEST'), false);
  assert.equal(redactLog('"refresh_token":"REFRESH_TEST"', []).includes('REFRESH_TEST'), false);
});
