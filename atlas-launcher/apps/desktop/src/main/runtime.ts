import { javaEnvironment } from './installation/java-environment';
import { createGameLog } from './installation/game-log';
import { compareVersions } from './modpack/versions';
import { readFile, writeFile, mkdir, unlink, stat } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { spawn, type ChildProcess } from 'node:child_process';
import { freemem } from 'node:os';
import { MicrosoftLogin } from './auth/microsoft';
import { TokenVault, type Cipher } from './auth/vault';
import { verifyManifestEnvelope, type ManifestTrust } from './modpack/manifest';
import {
  resolveGamePlan,
  installGame,
  expandArguments,
  type GamePlan,
} from './installation/minecraft';
import { installPack, recoverPack } from './installation/pack';
import { acquireInstallLock, processAlive } from './installation/lock';
import { TrustedTransport } from './installation/download';
import { GAME_ORIGINS } from './installation/minecraft';
import { ownedPath } from './installation/paths';
import { SettingsStore } from './settings';
import { PROJECT } from '../shared/project';
export interface InstallationState {
  status:
    | 'not-installed'
    | 'checking'
    | 'downloading-game'
    | 'downloading-pack'
    | 'ready'
    | 'running'
    | 'error'
    | 'cancelled';
  completed: number;
  total: number;
  label: string;
  message?: string;
  version?: string;
}
export class LauncherRuntime {
  readonly auth: MicrosoftLogin;
  onGameExit?: () => void;
  private controller?: AbortController;
  private running?: ChildProcess;
  private launching = false;
  private launchCancelled = false;
  private externalGamePid?: number;
  private plan?: GamePlan;
  private javaPath?: string;
  private installation: InstallationState = {
    status: 'not-installed',
    completed: 0,
    total: 0,
    label: 'Minecraft ainda não preparado.',
  };
  private constructor(
    private dataDirectory: string,
    private resources: string,
    private config: any,
    private envelope: string,
    private trust: ManifestTrust,
    private settings: SettingsStore,
    cipher: Cipher,
  ) {
    this.auth = new MicrosoftLogin(
      config.microsoftClientId,
      new TokenVault(join(dataDirectory, 'account-cache.bin'), cipher),
    );
  }
  static async create(
    dataDirectory: string,
    resources: string,
    settings: SettingsStore,
    cipher: Cipher,
  ) {
    const config = JSON.parse(await readFile(join(resources, 'launcher-config.json'), 'utf8'));
    const envelope = await readFile(join(resources, 'release.json'), 'utf8');
    const trust = {
      publicKeys: { 'atlas-release-2026': config.releasePublicKey },
      downloadOrigins: new Set<string>(config.downloadOrigins),
      bundledFiles: new Set<string>(config.bundledFiles),
    };
    const release = verifyManifestEnvelope(envelope, trust);
    if (compareVersions(PROJECT.version, release.minimumLauncherVersion) < 0)
      throw new Error('Atualize o launcher para instalar este modpack.');
    const runtime = new LauncherRuntime(
      dataDirectory,
      resources,
      config,
      envelope,
      trust,
      settings,
      cipher,
    );
    try {
      const saved = JSON.parse(await readFile(join(dataDirectory, 'game-process.json'), 'utf8'));
      if (processAlive(saved.pid)) runtime.externalGamePid = saved.pid;
    } catch {}
    return runtime;
  }
  state() {
    return {
      auth: this.auth.publicState(),
      installation: structuredClone(this.installation),
      canInstall: process.platform === 'win32' && process.arch === 'x64',
      minecraftVersion: '1.21.1',
      fabricVersion: '0.18.0',
      packVersion: verifyManifestEnvelope(this.envelope, this.trust).version,
      mods: verifyManifestEnvelope(this.envelope, this.trust).files.map((f) => ({
        name: f.path.slice(5),
        size: f.size,
      })),
      gameRunning: this.gameRunning(),
      busy: this.isBusy(),
    };
  }
  async install() {
    if (this.controller || this.gameRunning())
      throw new Error('Aguarde o processo atual terminar.');
    if (process.platform !== 'win32' || process.arch !== 'x64')
      throw new Error('A instalação automática desta versão está disponível no Windows x64.');
    const controller = new AbortController();
    this.controller = controller;
    this.installation = {
      status: 'checking',
      completed: 0,
      total: 0,
      label: 'Consultando Minecraft e Fabric oficiais…',
    };
    const root = join(this.dataDirectory, 'instances/atlas-cobblemon');
    const lock = join(root, '.atlas-install.lock');
    let handle;
    try {
      await ownedPath(root, '.atlas-install.lock');
      handle = await acquireInstallLock(lock);
      await recoverPack(root);
      const manifest = verifyManifestEnvelope(this.envelope, this.trust);
      this.plan = await resolveGamePlan(
        manifest.minecraftVersion,
        manifest.modLoader.version,
        new TrustedTransport(GAME_ORIGINS, fetch, controller.signal),
      );
      controller.signal.throwIfAborted();
      this.javaPath = await installGame(
        join(this.dataDirectory, 'minecraft'),
        this.plan,
        controller.signal,
        (completed, total, label) => {
          this.installation = { status: 'downloading-game', completed, total, label };
        },
      );
      await installPack(
        root,
        this.envelope,
        this.trust,
        join(this.resources, 'bundled'),
        controller.signal,
        (completed, total, label) => {
          this.installation = {
            status: 'downloading-pack',
            completed,
            total,
            label,
            version: manifest.version,
          };
        },
      );
      await this.writeServerList(root);
      this.installation = {
        status: 'ready',
        completed: manifest.files.length,
        total: manifest.files.length,
        label: 'Minecraft, Fabric e modpack verificados.',
        version: manifest.version,
      };
    } catch (error) {
      this.installation = {
        status: controller.signal.aborted ? 'cancelled' : 'error',
        completed: 0,
        total: 0,
        label: controller.signal.aborted
          ? 'Instalação cancelada.'
          : 'Não foi possível concluir a instalação.',
        message: error instanceof Error ? error.message : 'Tente novamente.',
      };
    } finally {
      if (handle) {
        await handle.close();
        await unlink(lock).catch(() => {});
      }
      this.controller = undefined;
    }
  }
  cancel() {
    this.controller?.abort();
    if (this.launching) this.launchCancelled = true;
  }
  private async writeServerList(root: string) {
    const options = await ownedPath(root, 'options.txt');
    try {
      await stat(options);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
      await writeFile(options, 'lang:pt_br\n', { flag: 'wx', mode: 0o600 });
    }

    const path = await ownedPath(root, 'servers.dat');
    try {
      await stat(path);
      return;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    }
    const nbtString = (value: string) => {
      const data = Buffer.from(value, 'utf8');
      const length = Buffer.alloc(2);
      length.writeUInt16BE(data.length);
      return Buffer.concat([length, data]);
    };
    const field = (name: string, value: string) =>
      Buffer.concat([Buffer.from([8]), nbtString(name), nbtString(value)]);
    const list = Buffer.alloc(4);
    list.writeUInt32BE(1);
    const data = Buffer.concat([
      Buffer.from([10, 0, 0, 9]),
      nbtString('servers'),
      Buffer.from([10]),
      list,
      field('name', 'Atlas Cobblemon'),
      field('ip', PROJECT.serverAddress),
      Buffer.from([0, 0]),
    ]);
    await (await import('node:fs/promises')).writeFile(path, data, { flag: 'wx', mode: 0o600 });
  }
  async play() {
    if (this.gameRunning() || this.controller || this.launching)
      throw new Error('Aguarde o jogo ou a instalação atual terminar.');
    if (this.installation.status !== 'ready')
      throw new Error('Prepare e verifique a instalação primeiro.');
    this.launching = true;
    this.launchCancelled = false;
    try {
      const requestedAccount = this.auth.publicState().account?.id;
      let account = await this.auth.forGame();
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      await this.install();
      if (this.installation.status !== 'ready' || !this.plan || !this.javaPath)
        throw new Error('A instalação precisa ser corrigida antes de jogar.');
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      if (!requestedAccount || this.auth.publicState().account?.id !== requestedAccount)
        throw new Error('A conta foi desconectada. Entre novamente antes de jogar.');
      account = await this.auth.forGame();
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      const preferences = await this.settings.read();
      if (preferences.ramMb < 4096)
        throw new Error('Configure pelo menos 4 GB de RAM para o modpack Atlas.');
      if (preferences.ramMb * 1048576 > freemem() - 1024 ** 3)
        throw new Error(
          'Memória livre insuficiente. Feche outros aplicativos ou reduza a RAM do jogo.',
        );
      const gameRoot = join(this.dataDirectory, 'minecraft');
      const instance = join(this.dataDirectory, 'instances/atlas-cobblemon');
      const plan = this.plan;
      const variables = {
        auth_player_name: account.profile.name,
        auth_uuid: account.profile.id,
        auth_access_token: account.accessToken,
        clientid: this.config.microsoftClientId,
        auth_xuid: account.xuid,
        user_type: 'msa',
        version_type: 'release',
        version_name: plan.versionId,
        game_directory: instance,
        assets_root: join(gameRoot, 'assets'),
        assets_index_name: plan.assetIndexId,
        natives_directory: join(gameRoot, 'natives', plan.versionId),
        launcher_name: 'Atlas Launcher',
        launcher_version: PROJECT.version,
        classpath: plan.classPath.map((path) => join(gameRoot, path)).join(';'),
        resolution_width: String(preferences.width),
        resolution_height: String(preferences.height),
      };
      const args = [
        `-Xmx${preferences.ramMb}M`,
        '-Xms512M',
        ...expandArguments(plan.vanilla.arguments.jvm, variables),
        ...expandArguments(plan.fabric.arguments?.jvm ?? [], variables),
        plan.fabric.mainClass,
        ...expandArguments(plan.vanilla.arguments.game, variables),
        ...expandArguments(plan.fabric.arguments?.game ?? [], variables),
        '--width',
        String(preferences.width),
        '--height',
        String(preferences.height),
        ...(preferences.fullscreen ? ['--fullscreen'] : []),
        '--quickPlayMultiplayer',
        PROJECT.serverAddress,
      ];
      if (!account.xuid) {
        const index = args.indexOf('--xuid');
        if (index >= 0) args.splice(index, 2);
      }
      const executable = await ownedPath(gameRoot, this.javaPath);
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      const log = await createGameLog(join(this.dataDirectory, 'diagnostics'), [
        account.accessToken,
      ]);
      if (this.launchCancelled) {
        await log.close();
        throw new Error('Inicialização cancelada.');
      }
      const child = spawn(executable, args, {
        cwd: instance,
        env: javaEnvironment(process.env, dirname(dirname(executable))),
        shell: false,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      child.stdout?.on('data', (chunk) => log.append(chunk, 0));
      child.stderr?.on('data', (chunk) => log.append(chunk, 1));
      child.once('close', () => void log.close().catch(() => {}));
      this.running = child;
      this.installation.status = 'running';
      child.once('error', () => {
        this.running = undefined;
        this.installation = {
          status: 'error',
          completed: 0,
          total: 0,
          label: 'Não foi possível iniciar o Java 21.',
        };
      });
      child.once('exit', (code) => {
        this.onGameExit?.();
        void unlink(join(this.dataDirectory, 'game-process.json')).catch(() => {});
        this.running = undefined;
        this.installation.status = code === 0 ? 'ready' : 'error';
        this.installation.label =
          code === 0
            ? 'Minecraft encerrado.'
            : 'O Minecraft encerrou com erro. Abra Configurações → Avançado → Diagnósticos.';
      });
      await new Promise<void>((resolve, reject) => {
        child.once('spawn', () => {
          void writeFile(
            join(this.dataDirectory, 'game-process.json'),
            JSON.stringify({ pid: child.pid }),
            { mode: 0o600 },
          )
            .then(() => resolve())
            .catch(() => {
              child.kill();
              reject(new Error('Não foi possível registrar o processo do jogo.'));
            });
        });
        child.once('error', () => reject(new Error('Java não iniciou.')));
      });
    } finally {
      this.launching = false;
    }
  }
  isBusy() {
    return !!this.controller || this.launching;
  }
  installing() {
    return !!this.controller;
  }
  gameRunning() {
    if (this.externalGamePid && !processAlive(this.externalGamePid))
      this.externalGamePid = undefined;
    return !!this.running || !!this.externalGamePid;
  }
}
