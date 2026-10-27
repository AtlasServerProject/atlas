import { lstat, mkdir } from 'node:fs/promises';
import { resolve, relative, isAbsolute, join, parse, sep } from 'node:path';
export function safeRelative(value: string): string {
  const parts = value.split('/');
  if (
    !value ||
    value.length > 450 ||
    isAbsolute(value) ||
    parts.some(
      (p) =>
        !p ||
        p === '.' ||
        p === '..' ||
        /[\\:%\x00-\x1f<>"|?*]/.test(p) ||
        /[. ]$/.test(p) ||
        /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(p),
    )
  )
    throw new Error('Caminho de instalação inválido.');
  return value;
}
export async function ownedPath(root: string, path: string): Promise<string> {
  safeRelative(path);
  const base = resolve(root);
  const target = resolve(base, ...path.split('/'));
  const rel = relative(base, target);
  if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('Caminho fora da instalação.');
  let ancestor = parse(base).root;
  for (const segment of base.slice(ancestor.length).split(sep).filter(Boolean)) {
    ancestor = join(ancestor, segment);
    try {
      const info = await lstat(ancestor);
      if (info.isSymbolicLink()) throw new Error('Link simbólico não permitido na instalação.');
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') break;
      throw error;
    }
  }
  await mkdir(base, { recursive: true, mode: 0o700 });
  let current = base;
  for (const part of ['', ...path.split('/')]) {
    if (part) current = join(current, part);
    try {
      const stat = await lstat(current);
      if (stat.isSymbolicLink() || (!stat.isDirectory() && stat.nlink > 1))
        throw new Error('Link simbólico não permitido na instalação.');
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    }
  }
  return target;
}
