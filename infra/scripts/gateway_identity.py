"""Authenticated IP envelope; no browser-supplied forwarded identity reaches Spring."""
import hashlib
import hmac
import ipaddress
import os
from pathlib import Path
import time

KEY_FILE = Path(os.environ.get('ATLAS_PROXY_KEY_FILE', Path(__file__).resolve().parents[2] / 'atlas-api/.runtime/proxy-hmac.key'))
IDENTITY_HEADERS = {'x-atlas-verified-ip', 'x-atlas-ip-time', 'x-atlas-ip-signature', 'x-real-ip', 'cf-connecting-ip', 'forwarded'}

def envelope(method, path, candidate, key=None, now=None):
    ip = str(ipaddress.ip_address(candidate))
    secret = KEY_FILE.read_text().strip().encode() if key is None else key
    if len(secret) < 43: raise ValueError('Private gateway key unavailable')
    timestamp = str(int(time.time() if now is None else now))
    message = f'{method}\n{path}\n{timestamp}\n{ip}'.encode()
    return {'X-Atlas-Verified-IP': ip, 'X-Atlas-IP-Time': timestamp,
            'X-Atlas-IP-Signature': hmac.new(secret, message, hashlib.sha256).hexdigest()}
