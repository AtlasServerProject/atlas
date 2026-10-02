#!/usr/bin/env python3
"""Local compiled SPA preview and fixed loopback API proxy. Production uses an HTTPS reverse proxy."""
import http.client
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2] / 'atlas-web/dist/atlas-web/browser'
ROUTES = {'/', '/how-to-play', '/store', '/notices', '/loja', '/login', '/cadastro', '/conta', '/minhas-compras', '/admin', '/recuperar-senha', '/verificar-email', '/redefinir-senha'}
API_PORT = int(os.environ.get('ATLAS_PREVIEW_API_PORT', '8080'))
PORT = int(os.environ.get('ATLAS_PREVIEW_PORT', '4200'))
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade', 'content-length'}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def proxy(self):
        if not urlsplit(self.path).path.startswith('/api/v1/'):
            return False
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0 or size > 65536:
                self.send_error(413); return True
            body = self.rfile.read(size) if size else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP and not k.lower().startswith('x-forwarded-')}
            conn = http.client.HTTPConnection('127.0.0.1', API_PORT, timeout=15)
            try:
                conn.request(self.command, self.path, body, headers)
                res = conn.getresponse(); data = res.read()
                self.send_response(res.status)
                for key, value in res.getheaders():
                    if key.lower() not in HOP: self.send_header(key, value)
                self.send_header('Content-Length', str(len(data))); self.end_headers()
                if self.command != 'HEAD': self.wfile.write(data)
            finally: conn.close()
        except (OSError, ValueError, http.client.HTTPException):
            self.send_response(503); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(b'{"code":"DEPENDENCY_UNAVAILABLE","message":"API temporariamente indisponivel."}')
        return True
    def do_GET(self):
        if self.proxy(): return
        if urlsplit(self.path).path.rstrip('/') in {r.rstrip('/') for r in ROUTES}: self.path = '/index.html'
        super().do_GET()
    def do_HEAD(self):
        if self.proxy(): return
        if urlsplit(self.path).path.rstrip('/') in {r.rstrip('/') for r in ROUTES}: self.path = '/index.html'
        super().do_HEAD()
    def do_POST(self):
        if not self.proxy(): self.send_error(405)
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_OPTIONS = do_POST
    def list_directory(self, path):
        self.send_error(404); return None
    def log_message(self, format, *args):
        # Avoid recording token or personal data from arbitrary query strings.
        return

if __name__ == '__main__':
    if not (ROOT / 'index.html').is_file(): raise SystemExit('Compile atlas-web com npm run build antes de iniciar.')
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
