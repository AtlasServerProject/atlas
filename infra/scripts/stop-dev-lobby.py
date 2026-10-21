#!/usr/bin/env python3
"""Ask the private Minecraft console to save/stop, then await process exit."""
import argparse
import os
from pathlib import Path
import socket
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pid", type=int, nargs="?", default=0, const=0)
parser.add_argument("--socket", type=Path, default=Path.home() / ".local/share/atlas-dev/fabric/atlas-admin.sock")
args = parser.parse_args()
if args.pid <= 1:
    # systemd also invokes ExecStop after a successful automatic idle shutdown.
    raise SystemExit(0)
try:
    with socket.socket(socket.AF_UNIX) as console:
        console.settimeout(8)
        console.connect(str(args.socket))
        console.sendall(b"stop\n")
        console.recv(8192)
except (OSError, TimeoutError):
    # The process may already have stopped or not yet reached server startup.
    pass
for _ in range(110):
    try:
        os.kill(args.pid, 0)
    except ProcessLookupError:
        break
    time.sleep(1)
