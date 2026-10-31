import { contextBridge, ipcRenderer } from 'electron';
import { CHANNELS, type AtlasBridge } from '../shared/contracts';
const bridge: AtlasBridge = {
  applyLauncherUpdate: () => ipcRenderer.invoke(CHANNELS.launcherApply),
  checkLauncherUpdates: () => ipcRenderer.invoke(CHANNELS.launcherCheck),
  downloadLauncherUpdate: () => ipcRenderer.invoke(CHANNELS.launcherDownload),
  openLauncherDownloads: () => ipcRenderer.invoke(CHANNELS.launcherFolder),
  signInOffline: (nickname) => ipcRenderer.invoke(CHANNELS.offline, nickname),
  checkUpdates: () => ipcRenderer.invoke(CHANNELS.updates),
  openDiagnostics: () => ipcRenderer.invoke(CHANNELS.diagnostics),
  runtimeState: () => ipcRenderer.invoke(CHANNELS.runtime),
  signInMicrosoft: () => ipcRenderer.invoke(CHANNELS.signIn),
  openMicrosoftVerification: () => ipcRenderer.invoke(CHANNELS.openMicrosoft),
  signOut: () => ipcRenderer.invoke(CHANNELS.signOut),
  installMinecraft: () => ipcRenderer.invoke(CHANNELS.install),
  cancelInstallation: () => ipcRenderer.invoke(CHANNELS.cancel),
  playMinecraft: () => ipcRenderer.invoke(CHANNELS.play),
  windowAction: (action) => ipcRenderer.invoke(CHANNELS.window, action),
  bootstrap: () => ipcRenderer.invoke(CHANNELS.bootstrap),
  saveSettings: (settings) => ipcRenderer.invoke(CHANNELS.saveSettings, settings),
  openWebsite: () => ipcRenderer.invoke(CHANNELS.website),
};
contextBridge.exposeInMainWorld('atlas', Object.freeze(bridge));
