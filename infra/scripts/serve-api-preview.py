#!/usr/bin/env python3
"""Expose only the API on a loopback port consumed by cloudflared."""
from http.server import ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location('atlas_preview', Path(__file__).with_name('serve-web.py'))
preview = module_from_spec(spec)
spec.loader.exec_module(preview)

class Handler(preview.Handler):
    def do_GET(self):
        if not self.proxy(): self.send_error(404)
    do_HEAD = do_GET

ThreadingHTTPServer(('127.0.0.1', 4201), Handler).serve_forever()
