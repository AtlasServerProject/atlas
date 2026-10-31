#!/usr/bin/env python3
"""Load plain environment values without evaluating shell code, then run the local API."""
import os
from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
file = root / '.env'
if not file.is_file(): raise SystemExit('Run scripts/init-local-env.py and provision the isolated database first.')
for line in file.read_text().splitlines():
    if not line.strip() or line.lstrip().startswith('#'): continue
    key, sep, value = line.partition('=')
    if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*',key): raise SystemExit('Invalid environment file; use KEY=value, without shell syntax.')
    os.environ.setdefault(key,value)
os.chdir(root)
os.execv(str(root/'mvnw'),[str(root/'mvnw'),'-B','-ntp','spring-boot:run'])
