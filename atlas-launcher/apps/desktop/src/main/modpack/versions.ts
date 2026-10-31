export function compareVersions(left: string, right: string): number {
  const parse = (value: string) => {
    const match = /^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$/.exec(value);
    if (!match || value.length > 200) throw new Error('Versão inválida.');
    return { numbers: match.slice(1, 4).map(BigInt), pre: match[4]?.split('.') };
  };
  const a = parse(left),
    b = parse(right);
  for (let i = 0; i < 3; i++)
    if (a.numbers[i] !== b.numbers[i]) return a.numbers[i] > b.numbers[i] ? 1 : -1;
  if (!a.pre && !b.pre) return 0;
  if (!a.pre) return 1;
  if (!b.pre) return -1;
  for (let i = 0; i < Math.max(a.pre.length, b.pre.length); i++) {
    const x = a.pre[i],
      y = b.pre[i];
    if (x === y) continue;
    if (x === undefined) return -1;
    if (y === undefined) return 1;
    const numericX = /^\d+$/.test(x),
      numericY = /^\d+$/.test(y);
    if (numericX && numericY) return BigInt(x) > BigInt(y) ? 1 : -1;
    if (numericX !== numericY) return numericX ? -1 : 1;
    return x > y ? 1 : -1;
  }
  return 0;
}
