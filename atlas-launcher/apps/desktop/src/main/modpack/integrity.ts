import { createHash } from 'node:crypto';
import type { ManagedFile } from './manifest';
export function verifyFileBytes(
  bytes: Uint8Array,
  expected: Pick<ManagedFile, 'size' | 'sha256'>,
): boolean {
  return (
    bytes.byteLength === expected.size &&
    createHash('sha256').update(bytes).digest('hex') === expected.sha256
  );
}
export function planFiles(
  files: readonly ManagedFile[],
  installed: ReadonlyMap<string, { size: number; sha256: string }>,
): { download: ManagedFile[]; unchanged: ManagedFile[] } {
  const download: ManagedFile[] = [];
  const unchanged: ManagedFile[] = [];
  for (const file of files) {
    const local = installed.get(file.path);
    (local?.size === file.size && local.sha256 === file.sha256 ? unchanged : download).push(file);
  }
  return { download, unchanged };
}
