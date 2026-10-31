import { spawn } from 'node:child_process';
import { managedInstall, mayApplyUpdate, installerArguments } from './launcher/install-policy';
import { mkdir, readFile } from 'node:fs/promises';
import { LauncherRuntime } from './runtime';
import { validateVerificationUri } from './auth/microsoft';
import { app, BrowserWindow, ipcMain, shell, session, safeStorage } from 'electron';
import { join, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { totalmem } from 'node:os';
import { CHANNELS } from '../shared/contracts';
import { SettingsStore, ramLimit } from './settings';
import { validateWindowAction } from './window-actions';
import { PROJECT } from '../shared/project';
import { trustedFrame } from './origins';
const development = !app.isPackaged && process.env.ATLAS_DEV_URL === 'http://127.0.0.1:5179';
const page = development
  ? 'http://127.0.0.1:5179/'
  : pathToFileURL(join(__dirname, 'renderer/index.html')).href;
app.setName('Atlas Launcher');
app.setAppUserModelId('br.com.atlascobblemon.launcher');
if (!app.requestSingleInstanceLock()) app.quit();
else {
  let window: BrowserWindow | null = null;
  app.on('second-instance', () => {
    window?.restore();
    window?.focus();
  });
  app
    .whenReady()
    .then(async () => {
      const max = ramLimit(totalmem());
      const directory = app.getPath('userData');
      const store = new SettingsStore(directory, max);
      const runtime = await LauncherRuntime.create(directory, join(__dirname, 'resources'), store, {
        available: () =>
          safeStorage.isEncryptionAvailable() &&
          (process.platform !== 'linux' ||
            safeStorage.getSelectedStorageBackend() !== 'basic_text'),
        encrypt: (value) => safeStorage.encryptString(value),
        decrypt: (bytes) => safeStorage.decryptString(bytes),
      });
      let installed = false;
      if (app.isPackaged && process.platform === 'win32') {
        try {
          installed = managedInstall(
            process.execPath,
            process.env.LOCALAPPDATA,
            JSON.parse(
              await readFile(join(dirname(process.execPath), '.atlas-installation.json'), 'utf8'),
            ),
          );
        } catch {}
      }
      runtime.launcherUpdates.configureAutomatic(installed);
      let applyingUpdate = false;
      let updateSpawned = false;
      let closingAfterGame = false;
      let gameCloseTimer: NodeJS.Timeout | undefined;
      async function applyUpdate(restart: boolean) {
        if (applyingUpdate) return;
        if (
          !mayApplyUpdate(
            installed,
            runtime.launcherUpdates.state.status === 'downloaded',
            runtime.gameRunning(),
            runtime.isBusy(),
          )
        )
          throw new Error('Encerre o Minecraft e aguarde as operações antes de atualizar.');
        applyingUpdate = true;
        try {
          const executable = await runtime.launcherUpdates.preparedInstaller();
          if (!executable) throw new Error('Nenhuma atualização verificada está pronta.');
          const child = spawn(executable, installerArguments(process.pid, restart), {
            detached: true,
            windowsHide: true,
            stdio: 'ignore',
            shell: false,
          });
          await new Promise<void>((resolve, reject) => {
            child.once('spawn', resolve);
            child.once('error', reject);
          });
          child.unref();
          updateSpawned = true;
          app.quit();
        } catch {
          applyingUpdate = false;
          runtime.launcherUpdates.state.status = 'error';
          throw new Error(
            'Não foi possível iniciar a atualização. O launcher atual foi preservado.',
          );
        }
      }
      session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) =>
        callback(false),
      );
      session.defaultSession.setPermissionCheckHandler(() => false);
      session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        const policy =
          "default-src 'self'; script-src 'self'" +
          (development ? " 'unsafe-inline'" : '') +
          "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'" +
          (development ? ' ws://127.0.0.1:5179' : '') +
          "; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'";
        callback({
          responseHeaders: { ...details.responseHeaders, 'Content-Security-Policy': [policy] },
        });
      });
      window = new BrowserWindow({
        width: 1280,
        icon: join(__dirname, 'renderer/assets/logo.png'),
        frame: false,
        height: 820,
        minWidth: 960,
        minHeight: 680,
        backgroundColor: '#080c1b',
        show: false,
        autoHideMenuBar: true,
        webPreferences: {
          preload: join(__dirname, 'preload.cjs'),
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
          webSecurity: true,
        },
      });
      window.webContents.once('did-finish-load', () => {
        void runtime.checkUpdates();
        void runtime.launcherUpdates.check();
      });
      const updateTimer = setInterval(
        () => {
          void runtime.checkUpdates();
          void runtime.launcherUpdates.check();
        },
        5 * 60 * 1000,
      );
      updateTimer.unref();
      runtime.onGameExit = () => {
        if (closingAfterGame) return;
        if (window && !window.isDestroyed()) {
          window.restore();
          window.show();
          window.focus();
        }
      };
      function handle(channel: string, action: (...args: unknown[]) => unknown) {
        ipcMain.handle(channel, (event, ...args: unknown[]) => {
          if (
            event.sender !== window?.webContents ||
            event.senderFrame !== window.webContents.mainFrame ||
            !trustedFrame(event.senderFrame?.url, page)
          )
            throw new Error('Origem não autorizada.');
          return action(...args);
        });
      }
      function noArgs(args: unknown[]) {
        if (args.length) throw new Error('Argumentos inválidos.');
      }
      handle(CHANNELS.diagnostics, async (...args) => {
        noArgs(args);
        const folder = join(directory, 'diagnostics');
        await mkdir(folder, { recursive: true, mode: 0o700 });
        const error = await shell.openPath(folder);
        if (error) throw new Error('Não foi possível abrir a pasta de diagnósticos.');
      });
      handle(CHANNELS.launcherApply, async (...args) => {
        noArgs(args);
        await applyUpdate(true);
      });
      handle(CHANNELS.launcherCheck, (...args) => {
        noArgs(args);
        void runtime.launcherUpdates.check();
      });
      handle(CHANNELS.launcherDownload, (...args) => {
        noArgs(args);
        void runtime.launcherUpdates.download().catch(() => {});
      });
      handle(CHANNELS.launcherFolder, async (...args) => {
        noArgs(args);
        const folder = runtime.launcherUpdates.directory;
        await mkdir(folder, { recursive: true, mode: 0o700 });
        const error = await shell.openPath(folder);
        if (error) throw new Error('Não foi possível abrir a pasta.');
      });
      handle(CHANNELS.updates, (...args) => {
        if (args.length) throw new Error('Argumentos inválidos.');
        void runtime.checkUpdates().catch(() => {});
      });
      handle(CHANNELS.runtime, (...args) => {
        noArgs(args);
        return runtime.state();
      });
      handle(CHANNELS.offline, async (...args) => {
        if (args.length !== 1 || runtime.isBusy() || runtime.gameRunning())
          throw new Error('Aguarde o processo atual terminar.');
        await runtime.auth.signInOffline(args[0]);
      });
      handle(CHANNELS.signIn, (...args) => {
        noArgs(args);
        if (!runtime.state().auth.configured)
          throw new Error('O aplicativo Microsoft do Atlas ainda precisa ser cadastrado.');
        void runtime.auth.signIn().catch(() => {});
      });
      handle(CHANNELS.openMicrosoft, async (...args) => {
        noArgs(args);
        const uri = runtime.state().auth.verificationUri;
        if (!uri) throw new Error('Inicie o login Microsoft primeiro.');
        await shell.openExternal(validateVerificationUri(uri));
      });
      handle(CHANNELS.signOut, async (...args) => {
        noArgs(args);
        await runtime.auth.signOut();
      });
      handle(CHANNELS.install, (...args) => {
        noArgs(args);
        if (!runtime.state().canInstall)
          throw new Error('Use o pacote Windows x64 para instalar o Minecraft.');
        if (runtime.isBusy() || runtime.gameRunning())
          throw new Error('Aguarde o processo atual terminar.');
        void runtime.install().catch(() => {});
      });
      handle(CHANNELS.cancel, (...args) => {
        noArgs(args);
        runtime.cancel();
        runtime.launcherUpdates.cancel();
      });
      handle(CHANNELS.play, async (...args) => {
        noArgs(args);
        await runtime.play();
        if ((await store.read()).minimizeOnLaunch) window?.minimize();
      });
      window.on('close', (event) => {
        if (installed && runtime.gameRunning()) {
          event.preventDefault();
          closingAfterGame = true;
          window?.hide();
          if (!gameCloseTimer) {
            gameCloseTimer = setInterval(() => {
              if (!runtime.gameRunning()) {
                clearInterval(gameCloseTimer);
                gameCloseTimer = undefined;
                window?.close();
              }
            }, 1000);
            gameCloseTimer.unref();
          }
          return;
        }
        if (applyingUpdate && !updateSpawned) {
          event.preventDefault();
          return;
        }
        if (
          !applyingUpdate &&
          mayApplyUpdate(
            installed,
            runtime.launcherUpdates.state.status === 'downloaded',
            runtime.gameRunning(),
            runtime.isBusy(),
          )
        ) {
          event.preventDefault();
          void applyUpdate(false).catch(() => {
            runtime.launcherUpdates.state.status = 'error';
            runtime.launcherUpdates.state.message =
              'Não foi possível aplicar a atualização. Tente novamente mais tarde.';
            window?.close();
          });
          return;
        }
        runtime.cancel();
        runtime.launcherUpdates.cancel();
        if (runtime.installing()) {
          event.preventDefault();
          const timer = setInterval(() => {
            if (!runtime.installing()) {
              clearInterval(timer);
              window?.close();
            }
          }, 100);
        }
      });
      handle(CHANNELS.bootstrap, async (...args) => {
        if (args.length) throw new Error('Argumentos inválidos.');
        return {
          version: app.getVersion(),
          platform: process.platform,
          maxRamMb: max,
          installationDirectory: join(directory, 'instances', 'atlas-cobblemon'),
          settings: await store.read(),
        };
      });
      handle(CHANNELS.saveSettings, (...args) => {
        if (args.length !== 1) throw new Error('Argumentos inválidos.');
        return store.save(args[0]);
      });
      handle(CHANNELS.window, (...args) => {
        if (args.length !== 1) throw new Error('Argumentos inválidos.');
        const action = validateWindowAction(args[0]);
        if (action === 'minimize') window?.minimize();
        else if (action === 'maximize') {
          if (window?.isMaximized()) window.unmaximize();
          else window?.maximize();
        } else window?.close();
      });
      handle(CHANNELS.website, async (...args) => {
        if (args.length) throw new Error('Argumentos inválidos.');
        await shell.openExternal(PROJECT.website);
      });
      window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
      window.webContents.on('will-navigate', (event) => event.preventDefault());
      window.webContents.on('will-redirect', (event) => event.preventDefault());
      window.webContents.on('will-attach-webview', (event) => event.preventDefault());
      window.once('ready-to-show', () => window?.show());
      void window.loadURL(page);
    })
    .catch(() => {
      console.error('Não foi possível iniciar o Atlas Launcher.');
      app.exit(1);
    });
  app.on('window-all-closed', () => app.quit());
}
