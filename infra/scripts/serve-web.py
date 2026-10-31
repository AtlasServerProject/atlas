#!/usr/bin/env python3
"""Local compiled SPA preview and fixed loopback API proxy. Production uses an HTTPS reverse proxy."""
import http.client
import os
import re
import socket
import threading
from gateway_identity import envelope, IDENTITY_HEADERS
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2] / 'atlas-web/dist/atlas-web/browser'
ROUTES = {'/', '/how-to-play', '/store', '/notices', '/loja', '/login', '/cadastro', '/conta', '/minhas-compras', '/admin', '/recuperar-senha', '/verificar-email', '/redefinir-senha', '/tickets', '/admin/tickets'}
def spa_route(path):
    return path.rstrip('/') in {r.rstrip('/') for r in ROUTES} or bool(re.fullmatch(r'/minhas-compras/[0-9a-fA-F-]{36}/comprovante/?', path))
API_PORT = int(os.environ.get('ATLAS_PREVIEW_API_PORT', '8080'))
PORT = int(os.environ.get('ATLAS_PREVIEW_PORT', '4200'))
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade', 'content-length'}

class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(*args, **kwargs)
    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try: super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise
    def process_request_thread(self, request, client_address):
        try: super().process_request_thread(request, client_address)
        finally: self.slots.release()

class Handler(SimpleHTTPRequestHandler):
    server_version = 'AtlasGateway'
    sys_version = ''
    trusted_cloudflare = False
    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' https://accounts.google.com/gsi/client; style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://accounts.google.com/gsi/; frame-src https://accounts.google.com/gsi/; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        super().end_headers()
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def proxy(self):
        if not urlsplit(self.path).path.startswith('/api/v1/'):
            return False
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) > 1:
                self.send_error(400); return True
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0 or size > 65536:
                self.send_error(413); return True
            body = self.rfile.read(size) if size else None
            if body is not None and len(body) != size:
                self.send_error(400); return True
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP | IDENTITY_HEADERS and not k.lower().startswith('x-forwarded-')}
            candidate = self.headers.get('CF-Connecting-IP') if self.trusted_cloudflare else self.client_address[0]
            headers.update(envelope(self.command, urlsplit(self.path).path, candidate))
            conn = http.client.HTTPConnection('127.0.0.1', API_PORT, timeout=15)
            try:
                conn.request(self.command, self.path, body, headers)
                res = conn.getresponse(); data = res.read(1048577)
                if len(data) > 1048576: raise ValueError("Upstream response too large")
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
        if spa_route(urlsplit(self.path).path): self.path = '/index.html'
        super().do_GET()
    def do_HEAD(self):
        if self.proxy(): return
        if spa_route(urlsplit(self.path).path): self.path = '/index.html'
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
    BoundedHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
