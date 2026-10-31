import { ramLimit } from '../settings';
const MIB = 1048576;
export function memoryStatus(totalBytes: number, availableBytes: number) {
  const totalMb = Math.max(0, Math.floor(totalBytes / MIB));
  const availableMb = Math.max(0, Math.floor(availableBytes / MIB));
  const usableMb = Math.max(
    0,
    Math.min(ramLimit(totalBytes), Math.floor((availableMb - 1024) / 256) * 256),
  );
  return {
    totalMb,
    availableMb,
    usableMb,
    recommendedMb:
      ramLimit(totalBytes) >= 4096 && availableMb >= 2048
        ? Math.min(6144, Math.max(4096, usableMb))
        : 0,
  };
}
export function chooseGameMemory(requestedMb: number, totalBytes: number, availableBytes: number) {
  if (!Number.isSafeInteger(requestedMb) || requestedMb < 512 || requestedMb > 32768)
    throw new Error('Configure um limite de RAM válido entre 512 MB e 32 GB.');
  const status = memoryStatus(totalBytes, availableBytes);
  // Free RAM is a snapshot, not proof that the JVM cannot start. Always attempt
  // a valid launch; Java/the game reports real allocation failures afterwards.
  const heapMb = Math.min(requestedMb, Math.max(512, status.usableMb), ramLimit(totalBytes));
  return { ...status, heapMb, adjusted: heapMb < requestedMb };
}
