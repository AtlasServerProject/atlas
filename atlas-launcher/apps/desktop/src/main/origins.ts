export function trustedFrame(actual: string | undefined, expected: string): boolean {
  if (!actual) return false;
  try {
    const a = new URL(actual);
    const e = new URL(expected);
    return a.href === e.href;
  } catch {
    return false;
  }
}
