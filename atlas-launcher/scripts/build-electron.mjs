import './licenses.mjs';
import { cp } from 'node:fs/promises';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
const app = fileURLToPath(new URL('../apps/desktop/', import.meta.url));
await build({
  entryPoints: [app + 'src/main/index.ts'],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node22',
  external: ['electron'],
  outfile: app + 'dist/main.cjs',
});
await build({
  entryPoints: [app + 'src/preload/index.ts'],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node22',
  external: ['electron'],
  outfile: app + 'dist/preload.cjs',
});

await cp(app + 'resources', app + 'dist/resources', { recursive: true });
