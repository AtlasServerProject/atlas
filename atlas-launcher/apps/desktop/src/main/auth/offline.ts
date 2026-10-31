import { createHash } from 'node:crypto';
export function offlineProfile(value: unknown) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_]{3,16}$/.test(value))
    throw new Error('Use um nick de 3 a 16 caracteres: letras, números ou sublinhado.');
  const bytes = createHash('md5')
    .update('OfflinePlayer:' + value, 'utf8')
    .digest();
  bytes[6] = (bytes[6] & 0x0f) | 0x30;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  return { id: bytes.toString('hex'), name: value, kind: 'offline' as const };
}
