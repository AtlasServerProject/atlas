import { readFile, readdir, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const app = join(root, 'apps/desktop');
const metadata = JSON.parse(await readFile(join(app, 'package.json'), 'utf8'));
const seen = new Set();
const notices = [
  'ATLAS LAUNCHER — THIRD-PARTY NOTICES',
  'Electron/Chromium notices accompany the runtime distribution.',
  '',
];
async function visit(name, parent) {
  const require = createRequire(parent);
  let entry;
  try {
    entry = require.resolve(name);
  } catch {
    return;
  }
  let dir = dirname(entry);
  let info;
  while (true) {
    try {
      const item = JSON.parse(await readFile(join(dir, 'package.json'), 'utf8'));
      if (item.name === name) {
        info = item;
        break;
      }
    } catch {}
    const next = dirname(dir);
    if (next === dir) return;
    dir = next;
  }
  const key = info.name + '@' + info.version;
  if (seen.has(key)) return;
  seen.add(key);
  const files = await readdir(dir);
  for (const file of files.filter((f) => /^(licen[cs]e|copying|notice)(\.[^.]+)?$/i.test(f))) {
    notices.push('='.repeat(72), key + ' — ' + file, await readFile(join(dir, file), 'utf8'));
  }
  for (const dependency of Object.keys(info.dependencies ?? {}))
    await visit(dependency, join(dir, 'package.json'));
}
for (const name of Object.keys(metadata.dependencies)) await visit(name, join(app, 'package.json'));
await writeFile(join(app, 'resources/THIRD-PARTY-NOTICES.txt'), notices.join('\n\n'));
console.log('Notices collected for ' + seen.size + ' runtime packages.');
