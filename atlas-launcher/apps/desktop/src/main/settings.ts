import { readFile, mkdir, writeFile, rename } from 'node:fs/promises';
import { join } from 'node:path';
import type { Settings } from '../shared/contracts';
export function ramLimit(totalBytes: number): number {
  return Math.max(0, Math.min(32768, Math.floor((totalBytes / 1048576 - 2048) / 256) * 256));
}
export function defaultSettings(max: number): Settings {
  return {
    ramMb: Math.min(4096, max),
    width: 1280,
    height: 720,
    fullscreen: false,
    minimizeOnLaunch: true,
  };
}
export function validateSettings(value: unknown, max: number): Settings {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Configurações inválidas.');
  const data = value as Record<string, unknown>;
  const keys = ['ramMb', 'width', 'height', 'fullscreen', 'minimizeOnLaunch'];
  if (
    Object.keys(data).length !== keys.length ||
    Object.keys(data).some((key) => !keys.includes(key))
  )
    throw new Error('Campos inválidos.');
  for (const [key, min, limit] of [
    ['ramMb', 512, max],
    ['width', 854, 7680],
    ['height', 480, 4320],
  ] as const) {
    const n = data[key];
    if (typeof n !== 'number' || !Number.isInteger(n) || n < min || n > limit)
      throw new Error('Valor de configuração fora do limite.');
  }
  if (typeof data.fullscreen !== 'boolean' || typeof data.minimizeOnLaunch !== 'boolean')
    throw new Error('Opção inválida.');
  return {
    ramMb: data.ramMb as number,
    width: data.width as number,
    height: data.height as number,
    fullscreen: data.fullscreen,
    minimizeOnLaunch: data.minimizeOnLaunch,
  };
}
export class SettingsStore {
  private pending: Promise<void> = Promise.resolve();
  constructor(
    private directory: string,
    private max: number,
  ) {}
  async read(): Promise<Settings> {
    try {
      return validateSettings(
        JSON.parse(await readFile(join(this.directory, 'settings.json'), 'utf8')),
        this.max,
      );
    } catch {
      return defaultSettings(this.max);
    }
  }
  save(value: unknown): Promise<Settings> {
    const valid = validateSettings(value, this.max);
    const operation = this.pending.then(async () => {
      await mkdir(this.directory, { recursive: true, mode: 0o700 });
      const target = join(this.directory, 'settings.json');
      await writeFile(target + '.tmp', JSON.stringify(valid, null, 2), { mode: 0o600 });
      await rename(target + '.tmp', target);
    });
    this.pending = operation.catch(() => {});
    return operation.then(() => valid);
  }
}
