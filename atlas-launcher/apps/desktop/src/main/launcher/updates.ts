import { verify, createHash } from 'node:crypto';
import { mkdir, open, rename, rm } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { join } from 'node:path';
import { compareVersions } from '../modpack/versions';
import {
  TrustedTransport,
  limitedBytes,
  downloadFile,
  fileMatches,
} from '../installation/download';
import { ownedPath, safeRelative } from '../installation/paths';
export const UPDATE_ORIGIN = 'https://www.atlascobblemon.com.br';
export const LAUNCHER_FEED = UPDATE_ORIGIN + '/launcher/windows/latest.json';
export interface LauncherRelease {
  schemaVersion: 1 | 2;
  version: string;
  platform: 'win32-x64';
  filename: string;
  size: number;
  sha256: string;
  parts: { path: string; size: number; sha256: string }[];
}
export function verifyLauncherRelease(envelope: string, publicKey: string): LauncherRelease {
  if (Buffer.byteLength(envelope) > 512 * 1024) throw new Error('Manifesto do launcher excessivo.');
  const signed = JSON.parse(envelope);
  if (
    signed.keyId !== 'atlas-release-2026' ||
    typeof signed.payload !== 'string' ||
    typeof signed.signature !== 'string'
  )
    throw new Error('Assinatura do launcher inválida.');
  const payload = Buffer.from(signed.payload, 'base64'),
    signature = Buffer.from(signed.signature, 'base64');
  if (signature.length !== 64 || !verify(null, payload, publicKey, signature))
    throw new Error('Assinatura do launcher inválida.');
  const release = JSON.parse(payload.toString('utf8'));
  if (
    ![1, 2].includes(release.schemaVersion) ||
    release.platform !== 'win32-x64' ||
    typeof release.version !== 'string'
  )
    throw new Error('Versão do launcher incompatível.');
  compareVersions(release.version, release.version);
  if (
    !(
      release.schemaVersion === 2
        ? /^Atlas-Launcher-[0-9A-Za-z.+-]+-Setup-x64\.exe$/
        : /^Atlas-Launcher-[0-9A-Za-z.+-]+-Windows-x64\.zip$/
    ).test(release.filename)
  )
    throw new Error('Nome do pacote inválido.');
  const hash = (x: unknown) => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
  if (
    !Number.isSafeInteger(release.size) ||
    release.size <= 0 ||
    release.size > 1024 ** 3 ||
    !hash(release.sha256) ||
    !Array.isArray(release.parts) ||
    release.parts.length < 1 ||
    release.parts.length > 128
  )
    throw new Error('Pacote inválido.');
  let total = 0;
  const paths = new Set();
  for (const part of release.parts) {
    if (typeof part.path !== 'string') throw new Error('Parte inválida.');
    safeRelative(part.path);
    if (
      !part.path.startsWith('launcher/files/') ||
      paths.has(part.path) ||
      !Number.isSafeInteger(part.size) ||
      part.size <= 0 ||
      part.size > 20 * 1024 ** 2 ||
      !hash(part.sha256)
    )
      throw new Error('Parte inválida.');
    paths.add(part.path);
    total += part.size;
  }
  if (total !== release.size) throw new Error('Tamanho do pacote inválido.');
  return release;
}
export class LauncherUpdates {
  state = {
    status: 'idle',
    message: 'Consulte atualizações do launcher.',
    version: '',
    completed: 0,
    total: 0,
  };
  private release?: LauncherRelease;
  private controller?: AbortController;
  private checking = false;
  private automatic = false;
  configureAutomatic(value: boolean) {
    this.automatic = value;
  }
  async preparedInstaller(): Promise<string | undefined> {
    if (
      !this.automatic ||
      this.state.status !== 'downloaded' ||
      this.release?.schemaVersion !== 2 ||
      compareVersions(this.release.version, this.currentVersion) <= 0
    )
      return;
    const path = await ownedPath(this.directory, this.release.filename);
    if (
      !(await fileMatches(path, {
        size: this.release.size,
        hash: this.release.sha256,
        algorithm: 'sha256',
      }))
    )
      throw new Error('Instalador inválido. Baixe a atualização novamente.');
    return path;
  }
  constructor(
    readonly directory: string,
    private publicKey: string,
    private currentVersion: string,
  ) {}
  async check() {
    if (this.checking || this.controller || (this.automatic && this.state.status === 'downloaded'))
      return;
    this.checking = true;
    this.state = {
      ...this.state,
      status: 'checking',
      message: 'Consultando versões do launcher no site Atlas…',
    };
    try {
      const transport = new TrustedTransport(
        new Set([UPDATE_ORIGIN]),
        fetch,
        AbortSignal.timeout(15000),
      );
      const response = await transport.fetch(LAUNCHER_FEED, { cache: 'no-store' });
      if (!response.ok)
        throw new Error('Não foi possível consultar o launcher. Tente novamente mais tarde.');
      const candidate = verifyLauncherRelease(
        Buffer.from(await limitedBytes(response, 512 * 1024)).toString('utf8'),
        this.publicKey,
      );
      const available = compareVersions(candidate.version, this.currentVersion) > 0;
      if (this.release && compareVersions(candidate.version, this.release.version) < 0)
        throw new Error('Catálogo antigo rejeitado.');
      this.release = candidate;
      this.state = {
        status: available ? 'available' : 'current',
        message: available
          ? `Launcher ${candidate.version} disponível.`
          : `Launcher ${this.currentVersion} atualizado.`,
        version: candidate.version,
        completed: 0,
        total: 0,
      };
    } catch {
      this.state = {
        ...this.state,
        status: 'error',
        message:
          'Não foi possível verificar a atualização do launcher. Sua instalação foi preservada.',
      };
    } finally {
      this.checking = false;
    }
    if (this.automatic && this.state.status === 'available' && this.release?.schemaVersion === 2)
      await this.download();
  }
  async download() {
    if (
      this.controller ||
      this.checking ||
      !this.release ||
      compareVersions(this.release.version, this.currentVersion) <= 0
    )
      throw new Error('Consulte uma nova versão primeiro.');
    const release = this.release;
    const controller = new AbortController();
    this.controller = controller;
    this.state = {
      ...this.state,
      status: 'downloading',
      message: 'Baixando pacote do launcher…',
      completed: 0,
      total: release.parts.length,
    };
    let partial: string | undefined;
    try {
      partial = await ownedPath(this.directory, release.filename + '.part');
      await mkdir(this.directory, { recursive: true, mode: 0o700 });
      const transport = new TrustedTransport(new Set([UPDATE_ORIGIN]), fetch, controller.signal);
      for (const part of release.parts) {
        await downloadFile(
          this.directory,
          {
            path: 'parts/' + part.sha256,
            url: UPDATE_ORIGIN + '/' + part.path,
            size: part.size,
            hash: part.sha256,
            algorithm: 'sha256',
          },
          transport,
          controller.signal,
        );
        this.state.completed++;
      }
      const handle = await open(partial, 'w', 0o600);
      const hash = createHash('sha256');
      let size = 0;
      try {
        for (const part of release.parts)
          for await (const chunk of createReadStream(join(this.directory, 'parts', part.sha256))) {
            controller.signal.throwIfAborted();
            hash.update(chunk);
            size += chunk.length;
            await handle.writeFile(chunk);
          }
      } finally {
        await handle.close();
      }
      if (size !== release.size || hash.digest('hex') !== release.sha256)
        throw new Error('Integridade do launcher inválida.');
      await rename(partial, await ownedPath(this.directory, release.filename));
      this.state = {
        ...this.state,
        status: 'downloaded',
        message:
          this.automatic && release.schemaVersion === 2
            ? 'Atualização pronta. Será instalada ao fechar o launcher, depois de encerrar o Minecraft.'
            : 'Instalador verificado. Abra a pasta e execute-o para instalar o launcher.',
      };
    } catch {
      if (partial) await rm(partial, { force: true }).catch(() => {});
      this.state = {
        ...this.state,
        status: 'error',
        message: controller.signal.aborted
          ? 'Download cancelado.'
          : 'Não foi possível baixar ou conferir o pacote. Tente novamente.',
      };
    } finally {
      this.controller = undefined;
    }
  }
  cancel() {
    this.controller?.abort();
  }
}
