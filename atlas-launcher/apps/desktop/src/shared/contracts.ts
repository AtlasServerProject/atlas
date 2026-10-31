import type { AuthState } from '../main/auth/microsoft';
import type { InstallationState } from '../main/runtime';
export interface Settings {
  ramMb: number;
  width: number;
  height: number;
  fullscreen: boolean;
  minimizeOnLaunch: boolean;
}
export interface Bootstrap {
  version: string;
  platform: string;
  maxRamMb: number;
  installationDirectory: string;
  settings: Settings;
}
export interface RuntimeState {
  gameDiagnostic?: import('./diagnostics').Diagnostic & { id: string };
  launcherUpdate?: {
    status: string;
    message: string;
    version: string;
    completed: number;
    total: number;
  };
  updates?: { status: string; message: string; checkedAt: string };
  memory?: { totalMb: number; availableMb: number; usableMb: number; recommendedMb: number };
  launchMessage?: string;
  auth: AuthState;
  installation: InstallationState;
  canInstall: boolean;
  minecraftVersion: string;
  fabricVersion: string;
  packVersion: string;
  mods: { name: string; size: number }[];
  gameRunning: boolean;
  busy: boolean;
}
export interface AtlasBridge {
  applyLauncherUpdate(): Promise<void>;
  checkLauncherUpdates(): Promise<void>;
  downloadLauncherUpdate(): Promise<void>;
  openLauncherDownloads(): Promise<void>;
  signInOffline(nickname: string): Promise<void>;
  checkUpdates(): Promise<void>;
  openDiagnostics(): Promise<void>;
  runtimeState(): Promise<RuntimeState>;
  signInMicrosoft(): Promise<void>;
  openMicrosoftVerification(): Promise<void>;
  signOut(): Promise<void>;
  installMinecraft(): Promise<void>;
  cancelInstallation(): Promise<void>;
  playMinecraft(): Promise<void>;
  windowAction(action: WindowAction): Promise<void>;
  bootstrap(): Promise<Bootstrap>;
  saveSettings(settings: Settings): Promise<Settings>;
  openWebsite(): Promise<void>;
}
export type WindowAction = 'minimize' | 'maximize' | 'close';
export const CHANNELS = {
  launcherApply: 'atlas:launcher:apply',
  launcherCheck: 'atlas:launcher:check',
  launcherDownload: 'atlas:launcher:download',
  launcherFolder: 'atlas:launcher:folder',
  offline: 'atlas:auth:offline',
  updates: 'atlas:updates:check',
  diagnostics: 'atlas:diagnostics',
  runtime: 'atlas:runtime',
  signIn: 'atlas:auth:signin',
  openMicrosoft: 'atlas:auth:open',
  signOut: 'atlas:auth:signout',
  install: 'atlas:install',
  cancel: 'atlas:install:cancel',
  play: 'atlas:play',
  bootstrap: 'atlas:bootstrap',
  saveSettings: 'atlas:settings:save',
  website: 'atlas:website',
  window: 'atlas:window',
} as const;
