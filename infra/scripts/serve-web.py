#!/usr/bin/env python3
"""Serve only the compiled Atlas SPA; no source files or directory listings."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path('/home/somente/dev/atlas/atlas-web/dist/atlas-web/browser')
ROUTES = {'/', '/how-to-play', '/store', '/notices'}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path.rstrip('/') in {r.rstrip('/') for r in ROUTES}:
            self.path = '/index.html'
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path.rstrip('/') in {r.rstrip('/') for r in ROUTES}:
            self.path = '/index.html'
        super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404)
        return None

if __name__ == '__main__':
    if not (ROOT / 'index.html').is_file():
        raise SystemExit('Compile atlas-web com npm run build antes de iniciar.')
    ThreadingHTTPServer(('0.0.0.0', 4200), Handler).serve_forever()
