#!/usr/bin/env python3
"""Create a new fictitious checkout using the sandbox's existing linked dev account."""
from pathlib import Path
from http.cookiejar import CookieJar
import argparse,json,os,subprocess,secrets,uuid,urllib.request,bcrypt
parser=argparse.ArgumentParser();parser.add_argument("--tier",type=int,choices=(1,2,3),default=1);args=parser.parse_args()
root=Path(__file__).resolve().parents[1];work=root/'.runtime/payment-sandbox';state=json.loads((work/'state.json').read_text());env=json.loads((work/'process-env.json').read_text());assert env['ATLAS_MP_MODE']=='test' and env['ATLAS_DELIVERY_MODE']=='test' and env['ATLAS_DB_URL']==f"jdbc:postgresql://127.0.0.1:{state['db_port']}/postgres" and state['db_port'] not in (5432,25432,55432)
def sql(query):
 p=subprocess.run(['/usr/lib/postgresql/18/bin/psql','-X','-h','127.0.0.1','-p',str(state['db_port']),'-U','atlas_api_bootstrap','-d','postgres','-v','ON_ERROR_STOP=1','-At'],input=query,env={**os.environ,'PGPASSWORD':env['ATLAS_BOOTSTRAP_PASSWORD']},capture_output=True,text=True)
 if p.returncode:raise SystemExit('Sandbox operation failed.')
 return p.stdout.strip()
original=str(uuid.UUID(state['order_id']));user=json.loads(sql(f"SELECT row_to_json(u) FROM (SELECT u.id,u.email FROM atlas_web.users u JOIN atlas_web.orders o ON o.user_id=u.id WHERE o.id='{original}') u"));account=str(uuid.UUID(user['id']));assert user['email'].endswith('@example.invalid')
assert sql(f"SELECT nickname FROM atlas_web.minecraft_links WHERE user_id='{account}' AND revoked_at IS NULL")=='VFSomente'
password=secrets.token_urlsafe(32);hashed=bcrypt.hashpw(password.encode(),bcrypt.gensalt(rounds=12)).decode();sql(f"UPDATE atlas_web.users SET password_hash='{hashed}' WHERE id='{account}'")
credentials=work/'checkout-account.json';credentials.write_text(json.dumps({'email':user['email'],'password':password}));credentials.chmod(0o600)
browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()));base=f"http://127.0.0.1:{state['api_port']}"
def call(path,body=None,extra=None):
 headers={'Content-Type':'application/json',**(extra or {})}
 if body is not None:
  csrf=call('/api/v1/auth/csrf');headers[csrf['headerName']]=csrf['token']
 req=urllib.request.Request(base+path,headers=headers,data=json.dumps(body).encode() if body is not None else None)
 with browser.open(req,timeout=20) as r:
  data=r.read();return json.loads(data) if data else None
call('/api/v1/auth/login',{'email':user['email'],'password':password});catalog=call('/api/v1/catalog');product=next(p for p in catalog['products'] if p['slug']==f'vip-{args.tier}')
order=call('/api/v1/orders/checkout',{'productId':product['id'],'server':'emerald','quantity':1,'productRevision':product['revision'],'catalogRevision':catalog['revision'],'expectedCents':product['finalCents']},{'Idempotency-Key':str(uuid.uuid4())});assert order['snapshot']['nickname']=='VFSomente'
checkout=call('/api/v1/orders/'+order['id']+'/payment',{});assert checkout['mode']=='test'
(work/('previous-checkout-'+original+'.json')).write_text(json.dumps(state));(work/('previous-checkout-'+original+'.json')).chmod(0o600)
state.update({'order_id':order['id'],'checkout_url':checkout['checkoutUrl'],'expires_at':order['expiresAt'],'amount_cents':order['totalCents']});(work/'state.json').write_text(json.dumps(state));(work/'state.json').chmod(0o600)
print(json.dumps({'nickname':'VFSomente','mode':'test','plan':product['name'],'amount_cents':order['totalCents'],'checkout_url':checkout['checkoutUrl'],'expires_at':order['expiresAt']}))
