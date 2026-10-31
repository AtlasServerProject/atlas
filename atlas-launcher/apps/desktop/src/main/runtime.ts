import { launcherDiagnostic, type Diagnostic } from '../shared/diagnostics';
import { LauncherUpdates } from './launcher/updates';
import { fetchRelease, selectRelease } from './modpack/updates';
import { javaEnvironment } from './installation/java-environment';
import { createGameLog, gameExitMessage } from './installation/game-log';
import { compareVersions } from './modpack/versions';
import { readFile, writeFile, mkdir, unlink, stat, rename } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { spawn, type ChildProcess } from 'node:child_process';
import { freemem, totalmem } from 'node:os';
import { chooseGameMemory, memoryStatus } from './installation/memory';
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
  diagnostic?: Diagnostic;
}
export class LauncherRuntime {
  readonly auth: MicrosoftLogin;
  readonly launcherUpdates: LauncherUpdates;
  onGameExit?: () => void;
  private checkingUpdates = false;
  private updates = {
    status: 'idle',
    message: 'Consulte novas versões do modpack.',
    checkedAt: '',
  };
  private controller?: AbortController;
  private running?: ChildProcess;
  private launchMessage = '';
  private gameDiagnostic?: Diagnostic & { id: string };
  private diagnosticSequence = 0;
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
    this.launcherUpdates = new LauncherUpdates(
      join(dataDirectory, 'launcher-updates'),
      config.releasePublicKey,
      PROJECT.version,
    );
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
    for (const receipt of [
      join(dataDirectory, 'release-cache.json'),
      join(dataDirectory, 'instances/atlas-cobblemon/.atlas/managed-release.json'),
    ]) {
      try {
        runtime.envelope = selectRelease(
          runtime.envelope,
          await readFile(receipt, 'utf8'),
          trust,
          PROJECT.version,
        );
      } catch {}
    }
    return runtime;
  }
  state() {
    return {
      auth: this.auth.publicState(),
      gameDiagnostic: this.gameDiagnostic,
      memory: memoryStatus(totalmem(), freemem()),
      launchMessage: this.launchMessage,
      updates: { ...this.updates },
      launcherUpdate: { ...this.launcherUpdates.state },
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
  async checkUpdates() {
    if (this.isBusy() || this.gameRunning()) return;
    this.checkingUpdates = true;
    this.updates = { status: 'checking', message: 'Consultando catálogo assinado…', checkedAt: '' };
    try {
      const previous = verifyManifestEnvelope(this.envelope, this.trust).version;
      const selected = selectRelease(
        this.envelope,
        await fetchRelease(),
        this.trust,
        PROJECT.version,
      );
      await mkdir(this.dataDirectory, { recursive: true });
      await writeFile(join(this.dataDirectory, 'release-cache.next.json'), selected, {
        mode: 0o600,
      });
      await rename(
        join(this.dataDirectory, 'release-cache.next.json'),
        join(this.dataDirectory, 'release-cache.json'),
      );
      this.envelope = selected;
      const version = verifyManifestEnvelope(selected, this.trust).version;
      if (version !== previous && this.installation.status === 'ready')
        this.installation = {
          ...this.installation,
          status: 'not-installed',
          label: 'Nova versão disponível. Atualize para continuar.',
        };
      this.updates = {
        status: version !== previous ? 'available' : 'current',
        message:
          version !== previous
            ? `Atlas ${version} disponível para instalar.`
            : `Atlas ${version}: catálogo atualizado.`,
        checkedAt: new Date().toISOString(),
      };
    } catch (error) {
      this.updates = {
        status: 'error',
        message:
          error instanceof Error
            ? error.message
            : 'Não foi possível consultar atualizações. A versão local foi preservada.',
        checkedAt: new Date().toISOString(),
      };
    } finally {
      this.checkingUpdates = false;
    }
  }
  async install(forLaunch = false) {
    if (
      this.controller ||
      this.checkingUpdates ||
      (this.launching && !forLaunch) ||
      this.gameRunning()
    )
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
        message: launcherDiagnostic(error).explanation,
        diagnostic: launcherDiagnostic(error),
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
      await this.install(true);
      if (this.installation.status !== 'ready' || !this.plan || !this.javaPath)
        throw new Error('A instalação precisa ser corrigida antes de jogar.');
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      if (!requestedAccount || this.auth.publicState().account?.id !== requestedAccount)
        throw new Error('A conta foi desconectada. Entre novamente antes de jogar.');
      account = await this.auth.forGame();
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      const preferences = await this.settings.read();
      const memory = chooseGameMemory(preferences.ramMb, totalmem(), freemem());
      this.launchMessage = memory.adjusted
        ? `Para esta sessão, o limite do jogo foi ajustado de ${(preferences.ramMb / 1024).toLocaleString('pt-BR')} GB para ${(memory.heapMb / 1024).toLocaleString('pt-BR')} GB, conforme a memória disponível. Sua preferência foi preservada.`
        : `Minecraft preparado com limite de ${(memory.heapMb / 1024).toLocaleString('pt-BR')} GB de RAM.`;
      const gameRoot = join(this.dataDirectory, 'minecraft');
      const instance = join(this.dataDirectory, 'instances/atlas-cobblemon');
      const plan = this.plan;
      const variables = {
        auth_player_name: account.profile.name,
        auth_uuid: account.profile.id,
        auth_access_token: account.accessToken,
        clientid: this.config.microsoftClientId ?? '',
        auth_xuid: account.xuid,
        user_type: account.profile.kind === 'offline' ? 'legacy' : 'msa',
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
        `-Xmx${memory.heapMb}M`,
        '-Xms512M',
        '-XX:+ExitOnOutOfMemoryError',
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
      for (const option of [
        ...(!account.xuid ? ['--xuid'] : []),
        ...(!this.config.microsoftClientId ? ['--clientId'] : []),
      ]) {
        const index = args.indexOf(option);
        if (index >= 0) args.splice(index, 2);
      }
      const executable = await ownedPath(gameRoot, this.javaPath);
      if (this.launchCancelled) throw new Error('Inicialização cancelada.');
      this.gameDiagnostic = undefined;
      const log = await createGameLog(
        join(this.dataDirectory, 'diagnostics'),
        account.profile.kind === 'offline' ? [] : [account.accessToken],
        (diagnostic) => {
          if (this.gameDiagnostic?.code === diagnostic.code) return;
          this.gameDiagnostic = { ...diagnostic, id: `${Date.now()}-${++this.diagnosticSequence}` };
        },
        account.profile.kind === 'offline',
      );
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
      let spawnFailed = false;
      child.stdout?.on('data', (chunk) => log.append(chunk, 0));
      child.stderr?.on('data', (chunk) => log.append(chunk, 1));
      child.once('close', () => void log.close().catch(() => {}));
      this.running = child;
      this.installation.status = 'running';
      child.once('error', (error: NodeJS.ErrnoException) => {
        spawnFailed = true;
        this.running = undefined;
        this.installation = {
          status: 'error',
          completed: 0,
          total: 0,
          label:
            error.code === 'ENOMEM'
              ? 'O sistema não conseguiu reservar memória para iniciar o Minecraft. Feche outros aplicativos e tente novamente.'
              : 'Não foi possível iniciar o Java 21.',
        };
      });
      child.once('close', (code) => {
        this.onGameExit?.();
        void unlink(join(this.dataDirectory, 'game-process.json')).catch(() => {});
        this.running = undefined;
        if (spawnFailed) return;
        this.installation.status = code === 0 ? 'ready' : 'error';
        this.installation.label = gameExitMessage(code, log.memoryFailure());
        if (code !== 0 && !this.gameDiagnostic) {
          const diagnostic = log.memoryFailure()
            ? launcherDiagnostic('OutOfMemoryError')
            : {
                code: 'ATL-GAME-001',
                title: 'O Minecraft encerrou com erro',
                explanation: `O processo terminou com código ${code ?? 'indisponível'}. Esse código sozinho não identifica a causa.`,
                steps: ['Abra os diagnósticos e informe à equipe a ação realizada antes da falha.'],
                responsibility: 'Jogador ou equipe Atlas' as const,
              };
          this.gameDiagnostic = { ...diagnostic, id: `${Date.now()}-${++this.diagnosticSequence}` };
        }
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
        child.once('error', (error: NodeJS.ErrnoException) =>
          reject(
            new Error(
              error.code === 'ENOMEM'
                ? 'O sistema não conseguiu reservar memória para iniciar o Minecraft. Feche outros aplicativos e tente novamente.'
                : 'Java não iniciou.',
            ),
          ),
        );
      });
    } finally {
      this.launching = false;
    }
  }
  isBusy() {
    return !!this.controller || this.launching || this.checkingUpdates;
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
