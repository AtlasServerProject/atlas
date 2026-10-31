import { verifyManifestEnvelope, type ManifestTrust } from './manifest';
import { compareVersions } from './versions';
import { TrustedTransport, limitedBytes } from '../installation/download';
export const RELEASE_FEED = 'https://www.atlascobblemon.com.br/launcher/modpack.json';
export function selectRelease(
  current: string,
  candidate: string,
  trust: ManifestTrust,
  launcherVersion: string,
): string {
  const before = verifyManifestEnvelope(current, trust);
  const after = verifyManifestEnvelope(candidate, trust);
  if (before.packId !== after.packId || before.channel !== after.channel)
    throw new Error('Canal de atualização incompatível.');
  if (compareVersions(after.minimumLauncherVersion, launcherVersion) > 0)
    throw new Error('Esta versão do modpack exige um launcher mais recente.');
  const comparison = compareVersions(after.version, before.version);
  if (comparison < 0) throw new Error('Atualização mais antiga rejeitada.');
  if (comparison === 0 && JSON.stringify(before) !== JSON.stringify(after))
    throw new Error('Conteúdo alterado sem nova versão.');
  return comparison > 0 ? candidate : current;
}
export async function fetchRelease(request: typeof fetch = fetch): Promise<string> {
  const transport = new TrustedTransport(
    new Set(['https://www.atlascobblemon.com.br']),
    request,
    AbortSignal.timeout(15000),
  );
  const response = await transport.fetch(RELEASE_FEED, { cache: 'no-store' });
  if (!response.ok) throw new Error('Catálogo remoto indisponível. A versão local foi preservada.');
  return new TextDecoder('utf-8', { fatal: true }).decode(
    await limitedBytes(response, 2 * 1024 * 1024),
  );
}
