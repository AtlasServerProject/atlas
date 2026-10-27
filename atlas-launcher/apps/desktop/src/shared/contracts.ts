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
