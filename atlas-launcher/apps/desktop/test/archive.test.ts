import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { extractArchive } from '../src/main/installation/archive';
test('extração lê arquivo compactado válido sem executar seu conteúdo', async () => {
  const root = await mkdtemp(join(tmpdir(), 'atlas-archive-'));
  try {
    await extractArchive(
      join(import.meta.dirname, 'fixtures/runtime-safe.zip'),
      root,
      new AbortController().signal,
    );
    assert.equal(
      await readFile(join(root, 'runtime/bin/example.dll'), 'utf8'),
      'NOT AN EXECUTABLE: TEST FIXTURE',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
test('extração rejeita traversal e symlink, inclusive em entradas não selecionadas', async () => {
  for (const fixture of ['runtime-escape.zip', 'runtime-symlink.zip']) {
    const root = await mkdtemp(join(tmpdir(), 'atlas-archive-reject-'));
    try {
      await assert.rejects(
        extractArchive(
          join(import.meta.dirname, 'fixtures', fixture),
          root,
          new AbortController().signal,
          () => false,
        ),
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  }
});
