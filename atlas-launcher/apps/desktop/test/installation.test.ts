import { validClientId } from '../src/main/auth/microsoft';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { rulesAllow, mavenPath, expandArguments } from '../src/main/installation/minecraft';
import { recoverPack } from '../src/main/installation/pack';
import { acquireInstallLock } from '../src/main/installation/lock';
import { verifyManifestEnvelope } from '../src/main/modpack/manifest';
import { fileMatches } from '../src/main/installation/download';
test('regras Minecraft não incluem demo, plataformas diferentes ou features desabilitadas', () => {
  assert.ok(rulesAllow(undefined));
  assert.equal(rulesAllow([{ action: 'allow', os: { name: 'osx' } }]), false);
  assert.equal(rulesAllow([{ action: 'allow', features: { is_demo_user: true } }]), false);
  assert.ok(rulesAllow([{ action: 'allow', os: { name: 'windows' } }]));
  assert.equal(
    mavenPath('net.fabricmc:fabric-loader:0.18.0'),
    'net/fabricmc/fabric-loader/0.18.0/fabric-loader-0.18.0.jar',
  );
  assert.throws(() => mavenPath('group:../../escape:1'));
  assert.deepEqual(expandArguments(['--username', '${name}'], { name: 'AtlasTest' }), [
    '--username',
    'AtlasTest',
  ]);
  assert.throws(() => expandArguments(['${missing}'], {}));
});
test('recuperação restaura arquivos/recibo anteriores e mantém dados pessoais', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-rollback-'));
  try {
    await mkdir(join(root, '.atlas/backup/mods'), { recursive: true });
    await mkdir(join(root, 'mods'));
    await mkdir(join(root, 'saves'));
    await writeFile(join(root, 'mods/a.jar'), 'new');
    await writeFile(join(root, 'mods/b.jar'), 'new-only');
    await writeFile(join(root, 'saves/world'), 'personal');
    await writeFile(join(root, '.atlas/backup/mods/a.jar'), 'old');
    await writeFile(join(root, '.atlas/managed-release.json'), 'new-receipt');
    await writeFile(join(root, '.atlas/managed-release.previous.json'), 'old-receipt');
    await writeFile(
      join(root, '.atlas/transaction.json'),
      JSON.stringify({
        paths: ['mods/a.jar', 'mods/b.jar'],
        existed: ['mods/a.jar'],
        hadPrevious: ['mods/a.jar'],
        hadReceipt: true,
        phase: 'applying',
      }),
    );
    await recoverPack(root);
    assert.equal(await readFile(join(root, 'mods/a.jar'), 'utf8'), 'old');
    await assert.rejects(readFile(join(root, 'mods/b.jar')));
    assert.equal(await readFile(join(root, 'saves/world'), 'utf8'), 'personal');
    assert.equal(await readFile(join(root, '.atlas/managed-release.json'), 'utf8'), 'old-receipt');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
test('lock impede instalações concorrentes', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-lock-'));
  const path = join(root, 'install.lock');
  try {
    const lock = await acquireInstallLock(path);
    await assert.rejects(acquireInstallLock(path), /andamento/);
    await lock.close();
    await unlink(path);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
test('catálogo Atlas distribuído é assinado e contém somente arquivos reais/autorizados', async () => {
  const root = join(import.meta.dirname, '../resources');
  const config = JSON.parse(await readFile(join(root, 'launcher-config.json'), 'utf8'));
  const manifest = verifyManifestEnvelope(await readFile(join(root, 'release.json'), 'utf8'), {
    publicKeys: { 'atlas-release-2026': config.releasePublicKey },
    downloadOrigins: new Set(config.downloadOrigins),
    bundledFiles: new Set(config.bundledFiles),
  });
  assert.equal(manifest.files.length, 57);
  assert.equal(manifest.minecraftVersion, '1.21.1');
  assert.equal(manifest.modLoader.version, '0.18.0');
  const own = manifest.files.find((f) => f.url.startsWith('atlas-bundled:'))!;
  assert.ok(
    await fileMatches(join(root, 'bundled', own.path.slice(5)), {
      size: own.size,
      hash: own.sha256,
      algorithm: 'sha256',
    }),
  );
  assert.ok(config.microsoftClientId === null || validClientId(config.microsoftClientId));
});

import { javaEnvironment } from '../src/main/installation/java-environment';
test('Java recebe somente ambiente necessário, sem segredos ou injeção de flags', () => {
  const env = javaEnvironment(
    {
      SystemRoot: 'C:/Windows',
      Path: 'system-path',
      JAVA_TOOL_OPTIONS: '-javaagent:untrusted',
      JDK_JAVA_OPTIONS: '-Xmx999G',
      _JAVA_OPTIONS: 'bad',
      OPENAI_API_KEY: 'TEST_SECRET',
      JAVA_HOME: 'old-java',
    },
    'owned-java',
  );
  assert.equal(env.SystemRoot, 'C:/Windows');
  assert.equal(env.Path, 'system-path');
  assert.equal(env.JAVA_HOME, 'owned-java');
  assert.equal(env.JAVA_TOOL_OPTIONS, undefined);
  assert.equal(env.OPENAI_API_KEY, undefined);
  assert.equal(env.JDK_JAVA_OPTIONS, undefined);
  assert.equal(env._JAVA_OPTIONS, undefined);
});
