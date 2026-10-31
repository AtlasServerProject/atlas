#!/usr/bin/env python3
"""One bridge instance; only polls PostgreSQL while idle, never the public API."""
import fcntl
import time
from pathlib import Path
from challonge import Client
from repository import Repository
from service import Service

if __name__ == '__main__':
    directory = Path.home() / '.local/share/atlas-tournament-bridge'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / 'worker.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        service = Service(Repository(), Client())
        print('Integração Challonge iniciada.', flush=True)
        while True:
            try:
                service.tick()
            except Exception:
                print('Integração aguardando recuperação; credenciais e respostas omitidas.', flush=True)
            time.sleep(5)
