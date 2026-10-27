/** Private preview: node infra/crates/serve-web-preview.mjs <Angular browser build> <asset export> [port]. */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const [build, exported, port = '4305'] = process.argv.slice(2);
if (!build || !exported || !/^\d{4,5}$/.test(port) || +port > 65535) throw new Error('Expected build directory, private asset directory and optional port');
const root = path.resolve(build), assets = path.resolve(exported);
if (!fs.existsSync(root + '/index.html') || !fs.existsSync(assets + '/catalogue.json')) throw new Error('Build or catalogue export missing');
const types = { '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpeg': 'image/jpeg', '.ico': 'image/x-icon', '.txt': 'text/plain', '.md': 'text/plain', '.html': 'text/html' };
const headers = fs.readFileSync(root + '/_headers', 'utf8').split('\n').map(l => l.trim()).filter(l => l.includes(':'));
const server = http.createServer((req, res) => {
  let host;
  try { host = new URL('http://' + req.headers.host).hostname; } catch { res.writeHead(400); res.end(); return; }
  if (!['localhost','127.0.0.1','[::1]'].includes(host)) { res.writeHead(403); res.end(); return; }
  const url = new URL(req.url, 'http://localhost');
  for (const line of headers) { const i = line.indexOf(':'); res.setHeader(line.slice(0,i), line.slice(i+1).trim().replace('; upgrade-insecure-requests', '')); }
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return; }
  // Never proxy account data or expose the isolated production API in this preview.
  if (url.pathname.startsWith('/api/')) { res.writeHead(503, {'Content-Type':'application/json'}); res.end(JSON.stringify({message:'API indisponível na prévia local.'})); return; }
  const keyAsset = url.pathname.startsWith('/pokemon/keys/');
  let decoded;
  try { decoded = decodeURIComponent(url.pathname); } catch { res.writeHead(400); res.end(); return; }
  const assetName = decoded === '/pokemon/keys/catalogue.json' ? 'catalogue.json' : decoded === '/pokemon/keys/NOTICE.txt' ? 'NOTICE.txt' : decoded.startsWith('/pokemon/keys/licenses/') ? decoded.slice('/pokemon/keys/'.length) : decoded.slice(1);
  const base = keyAsset ? assets : root;
  let file = path.resolve(base, keyAsset ? assetName : '.' + decoded);
  if (!file.startsWith(base + '/')) { res.writeHead(403); res.end(); return; }
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
    if (path.extname(url.pathname)) { res.writeHead(404); res.end(); return; }
    file = root + '/index.html';
  }
  res.setHeader('Content-Type', types[path.extname(file)] ?? 'application/octet-stream');
  res.setHeader('Cache-Control','no-store'); res.writeHead(200);
  if (req.method === 'HEAD') res.end(); else fs.createReadStream(file).on('error', () => res.destroy()).pipe(res);
});
server.listen(+port, '127.0.0.1', () => console.log(`Private preview: http://localhost:${port}/store/chaves/generation_3`));
