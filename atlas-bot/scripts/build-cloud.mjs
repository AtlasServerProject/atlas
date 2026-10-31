import { build } from 'esbuild';
await build({
  entryPoints: ['deploy/cloud-entry.js'],
  outfile: '.runtime/cloud-build/atlas-bot.js',
  bundle: true,
  platform: 'node',
  target: 'node24',
  format: 'esm',
  minify: true,
  external: ['bufferutil', 'utf-8-validate'],
  banner: { js: 'import {createRequire} from "node:module";const require=createRequire(import.meta.url);' },
});
console.log('Bundle cloud criado em .runtime/cloud-build/atlas-bot.js');
