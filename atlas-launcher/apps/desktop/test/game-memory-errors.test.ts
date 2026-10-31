import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createGameLog, gameExitMessage } from '../src/main/installation/game-log';
test('real JVM memory failure split across output chunks produces an actionable error', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'atlas-memory-error-'));
  try {
    const log = await createGameLog(directory, ['private-token']);
    log.append(Buffer.from('Starting Java\njava.lang.OutOfMem'), 1);
    log.append(Buffer.from('oryError: Java heap space\naccess_token=private-token\n'), 1);
    assert.equal(log.memoryFailure(), true);
    assert.match(gameExitMessage(1, log.memoryFailure()), /falta de memória/);
    assert.equal(gameExitMessage(0, log.memoryFailure()), 'Minecraft encerrado.');
    await log.close();
    assert.doesNotMatch(await readFile(log.path, 'utf8'), /private-token/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
test('ordinary game errors are not misreported as lack of RAM', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'atlas-ordinary-error-'));
  try {
    const log = await createGameLog(directory, []);
    log.append(Buffer.from('Mod incompatibility\n'), 1);
    assert.equal(log.memoryFailure(), false);
    assert.doesNotMatch(gameExitMessage(1, log.memoryFailure()), /falta de memória/);
    await log.close();
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
