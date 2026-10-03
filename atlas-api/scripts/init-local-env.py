#!/usr/bin/env python3
"""Generate local-only secrets without printing them; refuses to overwrite existing .env."""
from pathlib import Path
import os
import secrets
import base64

root = Path(__file__).resolve().parents[1]
target = root / '.env'
text = (root / '.env.example').read_text()
for key in ('ATLAS_DB_PASSWORD', 'ATLAS_MIGRATION_PASSWORD', 'ATLAS_BOOTSTRAP_PASSWORD'):
    text = text.replace(key + '=\n', key + '=' + secrets.token_urlsafe(32) + '\n')
text = text.replace('ATLAS_MAIL_ENCRYPTION_KEY=\n', 'ATLAS_MAIL_ENCRYPTION_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n')
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(text)
print('Created ignored .env with random local credentials (permissions 0600).')
