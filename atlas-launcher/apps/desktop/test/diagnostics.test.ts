import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { gameDiagnostic, launcherDiagnostic, diagnosticText } from '../src/shared/diagnostics';
import { createGameLog } from '../src/main/installation/game-log';
test('invalid-session guidance distinguishes offline policy from Microsoft session renewal', () => {
  const text = '[AtlasDiagnostic] code=AUTH_INVALID_SESSION';
  const offline = gameDiagnostic(text, true)!;
  assert.equal(offline.code, 'ATL-AUTH-001');
  assert.equal(offline.responsibility, 'Equipe Atlas');
  assert.match(offline.explanation, /pode estar exigindo/);
  assert.doesNotMatch(offline.explanation, /com certeza/);
  assert.match(diagnosticText(gameDiagnostic(text, false)!), /saia da conta Microsoft/);
});
test('actual disconnect markers classify flight, registry and network without remote payloads', () => {
  for (const [code, expected] of [
    ['SERVER_FLIGHT_DISABLED', 'ATL-SRV-001'],
    ['MOD_REGISTRY_MISMATCH', 'ATL-MOD-001'],
    ['NETWORK_RESET', 'ATL-NET-002'],
    ['NETWORK_UNREACHABLE', 'ATL-NET-001'],
    ['DISCONNECT_UNKNOWN', 'ATL-SRV-002'],
  ])
    assert.equal(gameDiagnostic(`[AtlasDiagnostic] code=${code}`)?.code, expected);
  assert.equal(gameDiagnostic('[CHAT] <player> Invalid session'), undefined);
  assert.equal(gameDiagnostic('[Render thread/INFO] Starting Minecraft'), undefined);
});
test('installation errors expose stable codes and steps, never raw secrets or local paths', () => {
  for (const [message, code] of [
    ['ENOTDIR: not a directory', 'ATL-FILE-001'],
    ['EPERM: locked', 'ATL-FILE-002'],
    ['Remoção de arquivo não gerenciado bloqueada.', 'ATL-FILE-003'],
    ['ENOSPC: full', 'ATL-DISK-001'],
    ['checksum mismatch', 'ATL-INTEGRITY-001'],
    ['Minecraft autorização — HTTP 403: refused', 'ATL-MS-403'],
  ]) {
    const d = launcherDiagnostic(new Error(`${message} C:\\Users\\Private\\token=secret`));
    assert.equal(d.code, code);
    assert.doesNotMatch(diagnosticText(d), /Private|secret|token=/);
  }
  assert.equal(launcherDiagnostic('unrecognized token=secret').code, 'ATL-UNKNOWN-001');
  assert.doesNotMatch(diagnosticText(launcherDiagnostic('unrecognized token=secret')), /secret/);
});
test('streamed disconnect evidence is detected while game is running, including final partial line', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'atlas-diagnostic-'));
  const codes: string[] = [];
  try {
    const log = await createGameLog(directory, ['private-token'], (d) => codes.push(d.code), true);
    log.append(Buffer.from('[Render thread/WARN] [AtlasDiagnostic] code=AUTH_IN'), 0);
    log.append(Buffer.from('VALID_SESSION\naccess_token=private-token\n'), 0);
    assert.deepEqual(codes, ['ATL-AUTH-001']);
    log.append(Buffer.from('[AtlasDiagnostic] code=SERVER_FLIGHT_DISABLED'), 1);
    await log.close();
    assert.deepEqual(codes, ['ATL-AUTH-001', 'ATL-SRV-001']);
    assert.doesNotMatch(await readFile(log.path, 'utf8'), /private-token/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
