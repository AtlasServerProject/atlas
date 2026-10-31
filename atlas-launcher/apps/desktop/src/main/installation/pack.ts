import { compareVersions } from '../modpack/versions';
import { readFile, mkdir, rename, writeFile, rm, lstat, copyFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import {
  verifyManifestEnvelope,
  validateManagedPath,
  type ManifestTrust,
  type Manifest,
} from '../modpack/manifest';
import { downloadFile, fileMatches, TrustedTransport } from './download';
import { ownedPath, safeRelative } from './paths';
interface Journal {
  paths: string[];
  hadPrevious: string[];
  existed: string[];
  hadReceipt: boolean;
  phase: 'applying' | 'committed';
}
async function exists(path: string) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}
export async function recoverPack(root: string): Promise<void> {
  const journalPath = await ownedPath(root, '.atlas/transaction.json');
  let journal: Journal;
  try {
    journal = JSON.parse(await readFile(journalPath, 'utf8'));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return;
    throw new Error('Registro de instalação inválido.');
  }
  if (
    !Array.isArray(journal.paths) ||
    !Array.isArray(journal.hadPrevious) ||
    !Array.isArray(journal.existed) ||
    typeof journal.hadReceipt !== 'boolean' ||
    !['applying', 'committed'].includes(journal.phase)
  )
    throw new Error('Registro de instalação inválido.');
  for (const path of [...journal.paths, ...journal.hadPrevious, ...journal.existed])
    validateManagedPath(path);
  if (journal.phase === 'applying')
    for (const path of [...journal.paths].reverse()) {
      const backup = await ownedPath(root, '.atlas/backup/' + path);
      const target = await ownedPath(root, path);
      if (await exists(backup)) {
        await rm(target, { force: true });
        await mkdir(dirname(target), { recursive: true });
        await rename(backup, target);
      } else if (!journal.existed.includes(path)) await rm(target, { force: true });
    }
  if (journal.phase === 'applying') {
    const receipt = await ownedPath(root, '.atlas/managed-release.json');
    const previous = await ownedPath(root, '.atlas/managed-release.previous.json');
    if (journal.hadReceipt && (await exists(previous))) await rename(previous, receipt);
    else if (!journal.hadReceipt) await rm(receipt, { force: true });
  }
  await rm(await ownedPath(root, '.atlas/managed-release.previous.json'), { force: true });
  await rm(await ownedPath(root, '.atlas/backup'), { recursive: true, force: true });
  await rm(journalPath, { force: true });
}
export async function installPack(
  root: string,
  envelope: string,
  trust: ManifestTrust,
  bundledRoot: string,
  signal: AbortSignal,
  onProgress: (completed: number, total: number, label: string) => void,
): Promise<Manifest> {
  const manifest = verifyManifestEnvelope(envelope, trust);
  await recoverPack(root);
  let previous: Manifest | undefined;
  try {
    previous = verifyManifestEnvelope(
      await readFile(await ownedPath(root, '.atlas/managed-release.json'), 'utf8'),
      trust,
    );
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT')
      throw new Error('A versão anterior precisa ser verificada antes de atualizar.');
  }
  if (previous && compareVersions(manifest.version, previous.version) < 0)
    throw new Error(
      'Este launcher contém um perfil mais antigo. Atualize o launcher antes de verificar a instalação.',
    );
  const transport = new TrustedTransport(trust.downloadOrigins);
  let completed = 0;
  const staging = '.atlas/staging';
  await mkdir(await ownedPath(root, staging), { recursive: true });
  for (const file of manifest.files) {
    signal.throwIfAborted();
    const target = await ownedPath(root, file.path);
    const expected = { size: file.size, hash: file.sha256, algorithm: 'sha256' as const };
    if (!(await fileMatches(target, expected))) {
      const url = new URL(file.url);
      if (url.protocol === 'atlas-bundled:') {
        const name = url.pathname.slice(1);
        if (!trust.bundledFiles?.has(name)) throw new Error('Recurso local não autorizado.');
        // Bundled resources are read-only and may live inside Electron's ASAR.
        // ownedPath creates directories and is reserved for writable instance paths.
        safeRelative(name);
        if (name.includes('/')) throw new Error('Recurso local inválido.');
        const source = join(bundledRoot, name);
        if (!(await fileMatches(source, expected)))
          throw new Error('Recurso do launcher corrompido.');
        const stage = await ownedPath(root, staging + '/' + file.path);
        await mkdir(dirname(stage), { recursive: true });
        await writeFile(stage, await readFile(source), { mode: 0o600 });
      } else
        await downloadFile(
          root,
          { ...expected, path: staging + '/' + file.path, url: file.url },
          transport,
          signal,
        );
    } else {
      await rm(await ownedPath(root, staging + '/' + file.path), { force: true });
    }
    onProgress(++completed, manifest.files.length, file.path);
  }
  const current = new Set(manifest.files.map((f) => f.path));
  const obsolete = (previous?.files ?? []).filter((f) => !current.has(f.path)).map((f) => f.path);
  for (const removal of manifest.removals) {
    // Obsolete paths can be absent on fresh installs, skipped releases and repairs.
    // Absence requires no mutation; existing files still require signed ownership.
    if (!(await exists(await ownedPath(root, removal)))) continue;
    if (!previous?.files.some((f) => f.path === removal))
      throw new Error('Remoção de arquivo não gerenciado bloqueada.');
    if (!obsolete.includes(removal)) obsolete.push(removal);
  }
  const changed = [] as string[];
  for (const file of manifest.files)
    if (await exists(await ownedPath(root, staging + '/' + file.path))) changed.push(file.path);
  const paths = [...changed, ...obsolete];
  const existed = [] as string[];
  for (const path of paths) if (await exists(await ownedPath(root, path))) existed.push(path);
  const hadReceipt = await exists(await ownedPath(root, '.atlas/managed-release.json'));
  if (hadReceipt)
    await copyFile(
      await ownedPath(root, '.atlas/managed-release.json'),
      await ownedPath(root, '.atlas/managed-release.previous.json'),
    );
  const journal: Journal = { paths, existed, hadPrevious: existed, hadReceipt, phase: 'applying' };
  const journalPath = await ownedPath(root, '.atlas/transaction.json');
  await writeFile(journalPath + '.tmp', JSON.stringify(journal), { mode: 0o600 });
  await rename(journalPath + '.tmp', journalPath);
  try {
    for (const path of paths) {
      signal.throwIfAborted();
      const target = await ownedPath(root, path);
      const backup = await ownedPath(root, '.atlas/backup/' + path);
      if (existed.includes(path)) {
        await mkdir(dirname(backup), { recursive: true });
        await rename(target, backup);
      }
      if (changed.includes(path)) {
        await mkdir(dirname(target), { recursive: true });
        await rename(await ownedPath(root, staging + '/' + path), target);
      }
    }
    for (const file of manifest.files)
      if (
        !(await fileMatches(await ownedPath(root, file.path), {
          size: file.size,
          hash: file.sha256,
          algorithm: 'sha256',
        }))
      )
        throw new Error('Falha na verificação final do modpack.');
    await writeFile(await ownedPath(root, '.atlas/managed-release.next.json'), envelope, {
      mode: 0o600,
    });
    signal.throwIfAborted();
    await rename(
      await ownedPath(root, '.atlas/managed-release.next.json'),
      await ownedPath(root, '.atlas/managed-release.json'),
    );
    journal.phase = 'committed';
    await writeFile(journalPath + '.tmp', JSON.stringify(journal), { mode: 0o600 });
    await rename(journalPath + '.tmp', journalPath);
    await recoverPack(root);
    return manifest;
  } catch (error) {
    await recoverPack(root);
    throw error;
  }
}
