import { open, readFile, unlink } from 'node:fs/promises';
export function processAlive(pid: number): boolean {
  if (!Number.isSafeInteger(pid) || pid < 1) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'EPERM';
  }
}
export async function acquireInstallLock(path: string) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const handle = await open(path, 'wx', 0o600);
      await handle.writeFile(String(process.pid));
      return handle;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
      const owner = Number(await readFile(path, 'utf8'));
      if (!Number.isSafeInteger(owner) || owner < 1 || processAlive(owner))
        throw new Error('Outra instalação está em andamento.');
      await unlink(path);
    }
  }
  throw new Error('Não foi possível reservar a instalação.');
}
