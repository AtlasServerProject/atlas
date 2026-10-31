#!/usr/bin/env python3
"""Republish the same compiled frontend when the free tunnel hostname changes.
Uses existing local Netlify CLI authentication; never stores credentials in source.
"""
import json
import fcntl
from pathlib import Path
import re
import subprocess
import urllib.request
import urllib.error

root = Path(__file__).resolve().parents[2]
web = root / 'atlas-web'
runtime = root / 'atlas-api/.runtime'
lock = (runtime/'tunnel-sync.lock').open('a')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
site = json.loads((web/'.netlify/state.json').read_text())
if site.get('siteId') != 'b4e5439a-682b-4348-b6e2-f3ba1540fcdb':
    raise SystemExit('Link this checkout to the Atlas Netlify site first.')
invocation = subprocess.check_output(['systemctl', '--user', 'show', 'atlas-api-tunnel', '--property=InvocationID', '--value'], text=True).strip()
if not re.fullmatch('[a-f0-9]{32}', invocation): raise SystemExit('Tunnel is not running.')
log = subprocess.check_output(['journalctl', '--user', '_SYSTEMD_INVOCATION_ID='+invocation, '--no-pager', '-o', 'cat'], text=True)
urls = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', log)
if not urls: raise SystemExit('Tunnel URL is not ready yet.')
url = urls[-1]
state = runtime / 'published-tunnel-url'
# Even an unchanged URL can expire while cloudflared keeps retrying.
expired = 'Unauthorized: Tunnel not found' in log
if expired:
    subprocess.run(['systemctl','--user','restart','atlas-api-tunnel.service'],check=True)
    raise SystemExit('Expired tunnel recreated; next timer run publishes its new address.')
try:
    with urllib.request.urlopen(url+'/api/v1/system', timeout=20) as response:
        if response.status != 200 or json.load(response).get('application') != 'atlas-api':
            raise SystemExit('Tunnel API is not ready.')
except (OSError, ValueError, urllib.error.URLError):
    # New Quick Tunnel names can encounter negative DNS caching on the VM.
    probe = subprocess.run(['curl', '--doh-url', 'https://cloudflare-dns.com/dns-query',
                            '--fail', '--silent', '--max-time', '20', url+'/api/v1/system'],
                           capture_output=True, text=True)
    try:
        valid = probe.returncode == 0 and json.loads(probe.stdout).get('application') == 'atlas-api'
    except ValueError:
        valid = False
    if not valid:
        failures = runtime/'tunnel-health-failures'
        count = int(failures.read_text()) + 1 if failures.exists() else 1
        failures.write_text(str(count))
        if count >= 3:
            try:
                with urllib.request.urlopen('http://127.0.0.1:4201/api/v1/system', timeout=5) as local:
                    healthy = local.status == 200
            except OSError: healthy = False
            if healthy:
                subprocess.run(['systemctl','--user','restart','atlas-api-tunnel.service'],check=True)
                failures.unlink(missing_ok=True)
                raise SystemExit('Unhealthy tunnel recreated; next timer run publishes its new address.')
        raise SystemExit('Tunnel DNS/API is not ready; the timer retries shortly.')
(runtime/'tunnel-health-failures').unlink(missing_ok=True)
if state.exists() and state.read_text().strip() == url:
    public_ok = False
    try:
        with urllib.request.urlopen('https://atlas-cobblemon.netlify.app/api/v1/system', timeout=10) as response:
            public_ok = response.status == 200 and json.load(response).get('application') == 'atlas-api'
    except (OSError, ValueError): pass
    failures = runtime/'public-proxy-failures'
    if public_ok:
        failures.unlink(missing_ok=True)
        raise SystemExit(0)
    count = int(failures.read_text()) + 1 if failures.exists() else 1
    failures.write_text(str(count))
    if count < 3: raise SystemExit('Public proxy health failed; checking again before republishing.')
    failures.unlink(missing_ok=True)

publish = runtime/'published-web'
if not (publish/'index.html').is_file():
    raise SystemExit('Build atlas-web before publishing the API proxy.')
redirects = f'/api/v1/* {url}/api/v1/:splat 200\n/* /index.html 200\n'
for path in [web/'public/_redirects', publish/'_redirects']:
    path.write_text(redirects)
clis = sorted((Path.home()/'.npm/_npx').glob('*/node_modules/netlify-cli/bin/run.js'))
if not clis: raise SystemExit('Install and authenticate netlify-cli first.')
node = Path.home()/'.local/bin/node'
if not node.is_file(): raise SystemExit('Install Node in ~/.local/bin for unattended publishing.')
result = subprocess.run([str(node),str(clis[0]),'deploy','--prod','--dir='+str(publish),'--no-build','--json',
                         '--message=Atualiza endereco do tunel gratuito da API'], cwd=web, capture_output=True, text=True)
if result.returncode: raise SystemExit('Netlify deployment failed; existing site is preserved. Check local CLI authentication and limits.')
data = json.loads(result.stdout)
if data.get('site_id') != 'b4e5439a-682b-4348-b6e2-f3ba1540fcdb':
    raise SystemExit('Unexpected Netlify site; check local site link.')
state.write_text(url+'\n'); state.chmod(0o600)
print('Netlify API tunnel updated successfully.')
