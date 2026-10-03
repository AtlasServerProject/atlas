#!/usr/bin/env python3
"""Run M1 against a disposable native PostgreSQL cluster. No Docker, sudo or game DB access.
Default: tests, package and restart/failure smoke tests. --serve keeps the API running until Ctrl+C.
"""
import argparse
from http.cookiejar import CookieJar
import re
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--serve', action='store_true')
parser.add_argument('--api-port', type=int)
parser.add_argument('--web-tests', action='store_true')
parser.add_argument('--core-tests', action='store_true')
args = parser.parse_args()
pg_bin = Path(os.environ.get('ATLAS_PG_BIN', '/usr/lib/postgresql/18/bin'))
for tool in ('initdb', 'pg_ctl', 'psql'):
    if not (pg_bin / tool).is_file():
        raise SystemExit(f'Missing {pg_bin / tool}; install PostgreSQL 18 tools or set ATLAS_PG_BIN.')

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

work = Path(tempfile.mkdtemp(prefix='atlas-api-m2-'))
work.chmod(0o700)
pg_port = free_port()
api_port = args.api_port or free_port()
env = os.environ.copy()
env.update({
    'ATLAS_BOOTSTRAP_PASSWORD': secrets.token_urlsafe(32),
    'ATLAS_MAIL_ENCRYPTION_KEY': base64.b64encode(secrets.token_bytes(32)).decode(),
    'ATLAS_LOCAL_MAIL_DIRECTORY': str(work / 'mail'),
    'ATLAS_MIGRATION_PASSWORD': secrets.token_urlsafe(32),
    'ATLAS_DB_PASSWORD': secrets.token_urlsafe(32),
    'ATLAS_DB_USERNAME': 'atlas_api_runtime',
    'ATLAS_MIGRATION_USERNAME': 'atlas_api_migrator',
    'ATLAS_DB_URL': f'jdbc:postgresql://127.0.0.1:{pg_port}/postgres',
    'ATLAS_TEST_DB_URL': f'jdbc:postgresql://127.0.0.1:{pg_port}/postgres',
    'ATLAS_TEST_ADMIN_PASSWORD': '',
    'ATLAS_CORE_KEY': secrets.token_urlsafe(32),
    'SPRING_PROFILES_ACTIVE': 'test',
    'ATLAS_PORT': str(api_port),
    'ATLAS_BIND_ADDRESS': '127.0.0.1',
})
env['ATLAS_TEST_ADMIN_PASSWORD'] = env['ATLAS_BOOTSTRAP_PASSWORD']
pwfile = work / 'init-password'
pwfile.write_text(env['ATLAS_BOOTSTRAP_PASSWORD'])
pwfile.chmod(0o600)
pg_running = False
api = None
api_log = None
web = None

def pg(action):
    global pg_running
    command = [str(pg_bin / 'pg_ctl'), '-D', str(work / 'data'), '-w', action]
    if action == 'start':
        command += ['-l', str(work / 'postgres.log'), '-o', f'-p {pg_port} -h 127.0.0.1 -k {work}']
    else:
        command += ['-m', 'fast']
    subprocess.run(command, env=env, check=True, stdout=subprocess.DEVNULL)
    pg_running = action == 'start'

admin_env = env.copy()
admin_env['PGPASSWORD'] = env['ATLAS_BOOTSTRAP_PASSWORD']
def sql(text):
    subprocess.run([str(pg_bin / 'psql'), '-X', '-h', '127.0.0.1', '-p', str(pg_port),
                    '-U', 'atlas_api_bootstrap', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
                   input=text, text=True, env=admin_env, check=True, stdout=subprocess.DEVNULL)

def start_api():
    global api, api_log
    api_log = open(work / 'api.log', 'a')
    api = subprocess.Popen(['java', '-jar', str(root / 'target/atlas-api-0.4.1.jar')],
                           env=env, cwd=root, stdout=api_log, stderr=subprocess.STDOUT)

def stop_api():
    global api, api_log
    if api and api.poll() is None:
        api.terminate()
        try: api.wait(timeout=20)
        except subprocess.TimeoutExpired:
            api.kill(); api.wait()
    if api_log: api_log.close()
    api = None

def http(path):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{api_port}{path}', timeout=6) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

def ready():
    for _ in range(60):
        if api.poll() is not None:
            raise RuntimeError(f'API failed to start; inspect local log {work / "api.log"}')
        try:
            if http('/actuator/health/readiness')[0] == 200: return
        except (OSError, ValueError): pass
        time.sleep(.5)
    raise RuntimeError('API readiness timed out')

try:
    subprocess.run([str(pg_bin / 'initdb'), '-D', str(work / 'data'), '-U', 'atlas_api_bootstrap',
                    '--auth=scram-sha-256', '--pwfile', str(pwfile), '--encoding=UTF8', '--no-locale'],
                   check=True, stdout=subprocess.DEVNULL)
    pwfile.unlink()
    pg('start')
    sql((root / 'infra/postgres/provision.sql').read_text())
    sql("CREATE TABLE public.core_sentinel (id INTEGER PRIMARY KEY); INSERT INTO public.core_sentinel VALUES (1);")
    subprocess.run([str(root / 'mvnw'), '-B', '-ntp', 'verify'], cwd=root, env=env, check=True)
    if args.core_tests:
        subprocess.run(['python3',str(root/'scripts/verify-core-identity.py')],env={**env,'ATLAS_CORE_TEST_ISOLATED':'yes'},check=True)
    start_api(); ready()
    status, first = http('/api/v1/system')
    assert status == 200 and first['schemaGeneration'] == 5
    assert http('/actuator/metrics')[0] == 401
    jar = CookieJar()
    browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def auth_post(path, body):
        csrf = json.load(browser.open(f'http://127.0.0.1:{api_port}/api/v1/auth/csrf'))
        request = urllib.request.Request(f'http://127.0.0.1:{api_port}/api/v1/auth/{path}', data=json.dumps(body).encode(),
            headers={'Content-Type':'application/json', csrf['headerName']:csrf['token']})
        with browser.open(request) as result:
            return json.load(result) if result.status == 200 else None
    test_email = secrets.token_hex(12)+'@example.invalid'
    test_password = secrets.token_urlsafe(24)
    auth_post('register', {'username':'Restart test','email':test_email,'password':test_password})
    me = auth_post('login', {'email':test_email,'password':test_password})
    stop_api(); start_api(); ready()
    assert json.load(browser.open(f'http://127.0.0.1:{api_port}/api/v1/users/me'))['id'] == me['id']
    auth_post('logout', {})
    assert http('/api/v1/system')[1]['initializedAt'] == first['initializedAt']
    print('PASS: packaged API starts; restart preserves accounts and authenticated sessions; metrics are protected.', flush=True)
    if args.web_tests:
        # Browser tests create their own disposable accounts. Privileged fixture access stays in this process.
        web_port = free_port()
        web_env = env.copy()
        web_env.update({'ATLAS_PREVIEW_PORT':str(web_port),'ATLAS_PREVIEW_API_PORT':str(api_port),
            'ATLAS_TEST_URL':f'http://127.0.0.1:{web_port}', 'ATLAS_E2E_CORE_API_URL':f'http://127.0.0.1:{api_port}', 'ATLAS_E2E_MAIL_DIRECTORY':str(work/'mail')})
        fixture = work/'e2e-accounts.json'
        web_env['ATLAS_E2E_ACCOUNTS_FILE'] = str(fixture)
        accounts = {}
        for role in ['USER'] + ['ADMIN']*9:
            email = secrets.token_hex(12)+'@example.invalid'; password=secrets.token_urlsafe(24)
            auth_post('register', {'username':'Atlas '+role,'email':email,'password':password})
            account = auth_post('login', {'email':email,'password':password})
            for _ in range(40):
                text = '\n'.join(f.read_text() for f in (work/'mail').glob('*.eml'))
                match = re.search(r'To: '+re.escape(email)+r'(?:(?!To:).)*?#token=([A-Za-z0-9_-]+)',text,re.S)
                if match: break
                time.sleep(.25)
            else: raise RuntimeError('Local verification email was not delivered')
            auth_post('verify-email', {'token':match[1]})
            if role == 'ADMIN':
                subprocess.run(['python3',str(root/'scripts/admin-role.py'),'--user-id',account['id'],'--role','ADMIN',
                    '--actor','isolated-e2e','--reason','Disposable browser test fixture'],env=env,check=True,stdout=subprocess.DEVNULL)
            if role == 'ADMIN' and not accounts.get('ADMIN'):
                # The CLI must leave the last administrator in place and record no revocation.
                subprocess.run(['python3',str(root/'scripts/admin-role.py'),'--user-id',account['id'],'--role','USER',
                    '--actor','isolated-e2e','--reason','Verify last ADMIN protection'],env=env,check=True,stdout=subprocess.DEVNULL)
                assert json.load(browser.open(f'http://127.0.0.1:{api_port}/api/v1/users/me'))['role']=='ADMIN'
            auth_post('logout', {})
            accounts.setdefault(role,[]).append({'email':email,'password':password})
        fixture.write_text(json.dumps(accounts));fixture.chmod(0o600)
        # Initial HTTP tests may have used the same loopback IP; start the browser budget fresh.
        sql('DELETE FROM atlas_web.auth_rate_limits;')
        web = subprocess.Popen(['python3',str(root.parent/'infra/scripts/serve-web.py')],env=web_env)
        time.sleep(.5)
        subprocess.run(['npm','run','test:e2e'],cwd=root.parent/'atlas-web',env=web_env,check=True)
        print('PASS: browser authentication, recovery and storefront regressions.',flush=True)
    if args.serve:
        print(f'Isolated API ready at http://127.0.0.1:{api_port}/api/v1/system ; Ctrl+C to stop and discard.', flush=True)
        while api.poll() is None: time.sleep(1)
    else:
        pg('stop')
        assert http('/actuator/health/readiness')[0] == 503
        assert http('/actuator/health/liveness')[0] == 200
        assert http('/api/v1/system')[0] == 503
        stop_api(); start_api()
        assert api.wait(timeout=30) != 0, 'Startup must fail with unavailable database'
        stop_api(); pg('start'); start_api(); ready()
        for _ in range(20):
            if http('/actuator/health/readiness')[0] == 200: break
            time.sleep(.5)
        else: raise RuntimeError('Readiness did not recover after database restart')
        print('PASS: DB failure returns readiness 503, keeps liveness UP; startup fails closed and recovers.', flush=True)
except KeyboardInterrupt:
    print('Stopped isolated demo.')
finally:
    if web:
        web.terminate();web.wait(timeout=10)
    stop_api()
    if pg_running: pg('stop')
    if os.environ.get('ATLAS_KEEP_TEST_LOGS') == '1':
        print(f'Private test files retained at {work}; remove when finished.')
    else:
        shutil.rmtree(work)
