#!/usr/bin/env python3
"""Expose only the API on a loopback port consumed by cloudflared."""
from http.server import ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

spec = spec_from_file_location('atlas_preview', Path(__file__).with_name('serve-web.py'))
preview = module_from_spec(spec)
spec.loader.exec_module(preview)

PACK_ROOT = Path(__file__).resolve().parents[2] / 'infra/resourcepacks'
class Handler(preview.Handler):
    def resource_pack(self):
        match = re.fullmatch(r'/minecraft/resourcepacks/((?:atlas-gts-e19|atlas-textures)-[0-9a-f]{16}\.zip)', urlsplit(self.path).path)
        if not match: return False
        path = PACK_ROOT / match.group(1)
        if not path.is_file(): self.send_error(404); return True
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        if match.group(1).startswith('atlas-textures-'): self.send_header('Content-Disposition', 'attachment; filename="Atlas Textures.zip"')
        self.send_header('Content-Length', str(path.stat().st_size))
        self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            with path.open('rb') as data: shutil.copyfileobj(data, self.wfile)
        return True
    def do_GET(self):
        if not self.resource_pack() and not self.proxy(): self.send_error(404)
    do_HEAD = do_GET

ThreadingHTTPServer(('127.0.0.1', 4201), Handler).serve_forever()
