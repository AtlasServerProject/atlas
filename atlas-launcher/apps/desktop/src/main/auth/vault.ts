import { mkdir, readFile, writeFile, rename, unlink } from 'node:fs/promises';
import { dirname } from 'node:path';
export interface Cipher {
  available(): boolean;
  encrypt(value: string): Buffer;
  decrypt(value: Buffer): string;
}
export class TokenVault {
  private pending: Promise<void> = Promise.resolve();
  private generation = 0;
  constructor(
    private path: string,
    private cipher: Cipher,
  ) {}
  async read(): Promise<string | undefined> {
    await this.pending;
    if (!this.cipher.available()) return;
    try {
      return this.cipher.decrypt(await readFile(this.path));
    } catch {
      return;
    }
  }
  write(value: string): Promise<void> {
    const generation = this.generation;
    const operation = this.pending.then(async () => {
      if (generation !== this.generation || !this.cipher.available()) return;
      await mkdir(dirname(this.path), { recursive: true, mode: 0o700 });
      await writeFile(this.path + '.tmp', this.cipher.encrypt(value), { mode: 0o600 });
      if (generation !== this.generation) {
        await unlink(this.path + '.tmp').catch(() => {});
        return;
      }
      await rename(this.path + '.tmp', this.path);
    });
    this.pending = operation.catch(() => {});
    return operation;
  }
  clear(): Promise<void> {
    this.generation++;
    const operation = this.pending.then(async () => {
      for (const path of [this.path, this.path + '.tmp'])
        await unlink(path).catch((error) => {
          if (error.code !== 'ENOENT') throw error;
        });
    });
    this.pending = operation.catch(() => {});
    return operation;
  }
}
