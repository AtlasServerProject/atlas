import { createHash, sign } from 'node:crypto';
import { open, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, basename, resolve } from 'node:path';
import { homedir } from 'node:os';
const source = resolve(process.argv[2] ?? '');
const version = JSON.parse(await readFile('apps/desktop/package.json', 'utf8')).version;
const expected = `Atlas-Launcher-${version}-Setup-x64.exe`;
if (basename(source) !== expected)
  throw Error('Provide the Windows installer matching this version.');
const web = resolve('../atlas-web'),
  publicRoot = join(web, 'public/launcher/windows');
const files = join(web, '.launcher-distribution/launcher/files', version + '-installer');
await mkdir(files, { recursive: true });
await mkdir(publicRoot, { recursive: true });
const handle = await open(source, 'r'),
  parts = [],
  hash = createHash('sha256');
let size = 0;
try {
  for (let i = 0; ; i++) {
    const buffer = Buffer.alloc(20 * 1024 ** 2);
    let length = 0;
    while (length < buffer.length) {
      const result = await handle.read(buffer, length, buffer.length - length, null);
      if (!result.bytesRead) break;
      length += result.bytesRead;
    }
    if (!length) break;
    const bytes = buffer.subarray(0, length),
      name = String(i).padStart(3, '0') + '.bin';
    await writeFile(join(files, name), bytes);
    hash.update(bytes);
    size += length;
    parts.push({
      path: `launcher/files/${version}-installer/${name}`,
      size: length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
    });
  }
} finally {
  await handle.close();
}
const payload = Buffer.from(
  JSON.stringify({
    schemaVersion: 2,
    version,
    platform: 'win32-x64',
    filename: expected,
    size,
    sha256: hash.digest('hex'),
    parts,
  }),
);
const privateKey = await readFile(
  join(homedir(), '.config/atlas-launcher-publisher/release-ed25519.pem'),
);
await writeFile(
  join(publicRoot, 'latest.json'),
  JSON.stringify(
    {
      keyId: 'atlas-release-2026',
      payload: payload.toString('base64'),
      signature: sign(null, payload, privateKey).toString('base64'),
    },
    null,
    2,
  ) + '\n',
);
await writeFile(
  join(web, 'public/launcher/modpack.json'),
  await readFile('apps/desktop/resources/release.json'),
);
console.log(
  `Signed Windows installer ${version} prepared in ${parts.length} parts. Legacy ZIP feed preserved.`,
);
