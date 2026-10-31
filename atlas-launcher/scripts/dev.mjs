import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../apps/desktop/package.json', import.meta.url));
const cwd = fileURLToPath(new URL('../apps/desktop/', import.meta.url));
await import('./build-electron.mjs');
const vite = spawn(
  process.execPath,
  [join(dirname(require.resolve('vite/package.json')), 'bin/vite.js')],
  { cwd, stdio: 'inherit' },
);
let desktop;
let viteExited = false;
function stop() {
  desktop?.kill();
  vite.kill();
}
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
vite.on('exit', () => {
  viteExited = true;
  desktop?.kill();
});
try {
  let ready = false;
  for (let n = 0; n < 100; n++) {
    try {
      const response = await fetch('http://127.0.0.1:5179');
      if (response.ok) {
        ready = true;
        break;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (!ready || viteExited) throw new Error('Vite não iniciou na porta 5179.');
  const env = { ...process.env, ATLAS_DEV_URL: 'http://127.0.0.1:5179' };
  delete env.ELECTRON_RUN_AS_NODE;
  desktop = spawn(require('electron'), ['.'], { cwd, stdio: 'inherit', env });
  desktop.on('exit', (code) => {
    vite.kill();
    process.exitCode = code ?? 1;
  });
} catch (error) {
  stop();
  console.error(error.message);
  process.exitCode = 1;
}
