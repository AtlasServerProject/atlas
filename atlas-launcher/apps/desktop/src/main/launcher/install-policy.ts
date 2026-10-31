import { win32 } from 'node:path';
export const APP_ID = 'br.com.atlascobblemon.launcher';
export function managedInstall(
  executable: string,
  localAppData: string | undefined,
  marker: unknown,
): boolean {
  if (
    !localAppData ||
    !win32.isAbsolute(localAppData) ||
    !marker ||
    typeof marker !== 'object' ||
    (marker as Record<string, unknown>).appId !== APP_ID
  )
    return false;
  return (
    win32.normalize(executable).toLowerCase() ===
    win32.join(localAppData, 'Programs', 'AtlasLauncher', 'AtlasLauncher.exe').toLowerCase()
  );
}
export function mayApplyUpdate(
  installed: boolean,
  downloaded: boolean,
  gameRunning: boolean,
  busy: boolean,
): boolean {
  return installed && downloaded && !gameRunning && !busy;
}
export function installerArguments(parentPid: number, restart: boolean): string[] {
  if (!Number.isSafeInteger(parentPid) || parentPid <= 0)
    throw new Error('Processo de atualização inválido.');
  return ['/S', `/PARENT_PID=${parentPid}`, ...(restart ? ['/RESTART=1'] : [])];
}
