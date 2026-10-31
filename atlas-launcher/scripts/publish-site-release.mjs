import { createHash, sign } from 'node:crypto';
import { open, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, basename, resolve } from 'node:path';
import { homedir } from 'node:os';
const zip = resolve(process.argv[2] ?? '');
const version = JSON.parse(await readFile('apps/desktop/package.json', 'utf8')).version;
const expected = `Atlas-Launcher-${version}-Windows-x64.zip`;
if (basename(zip) !== expected) throw Error('Provide the built ZIP matching the launcher version.');
const web = resolve('../atlas-web'),
  publicRoot = join(web, 'public/launcher');
const files = join(web, '.launcher-distribution/launcher/files', version);
await mkdir(files, { recursive: true });
await mkdir(publicRoot, { recursive: true });
const source = await open(zip, 'r'),
  parts = [],
  hash = createHash('sha256');
let total = 0;
try {
  for (let index = 0; ; index++) {
    const buffer = Buffer.alloc(20 * 1024 ** 2);
    let length = 0;
    while (length < buffer.length) {
      const { bytesRead } = await source.read(buffer, length, buffer.length - length, null);
      if (!bytesRead) break;
      length += bytesRead;
    }
    if (!length) break;
    const bytes = buffer.subarray(0, length);
    const name = String(index).padStart(3, '0') + '.bin';
    await writeFile(join(files, name), bytes);
    hash.update(bytes);
    total += length;
    parts.push({
      path: `launcher/files/${version}/${name}`,
      size: length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
    });
  }
} finally {
  await source.close();
}
const release = {
  schemaVersion: 1,
  version,
  platform: 'win32-x64',
  filename: expected,
  size: total,
  sha256: hash.digest('hex'),
  parts,
};
const payload = Buffer.from(JSON.stringify(release));
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
  join(publicRoot, 'modpack.json'),
  await readFile('apps/desktop/resources/release.json'),
);
console.log(
  `Prepared signed launcher ${version}, ${parts.length} static parts. Private key not copied.`,
);
