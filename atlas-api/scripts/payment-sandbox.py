#!/usr/bin/env python3
"""Prepare a persistent, loopback-only payment sandbox. No production DB writes."""
import base64,json,os,secrets,socket,subprocess,time,uuid,urllib.request,urllib.error,sys,signal
from pathlib import Path
from http.cookiejar import CookieJar
root=Path(__file__).resolve().parents[1]
work=root/'.runtime/payment-sandbox';pg=Path('/usr/lib/postgresql/18/bin')
if len(sys.argv)>1:
 if sys.argv[1] not in ('--status','--stop'):raise SystemExit('Use --status or --stop.')
 state=json.loads((work/'state.json').read_text());stored=json.loads((work/'process-env.json').read_text())
 if stored['ATLAS_DB_URL']!=f"jdbc:postgresql://127.0.0.1:{state['db_port']}/postgres" or state['db_port']==55432:raise SystemExit('Unexpected sandbox database.')
 if sys.argv[1]=='--stop':
  pid=state['api_pid'];proc=Path('/proc')/str(pid)
  if proc.exists():
   current=dict(x.split('=',1) for x in (proc/'environ').read_text().split('\0') if '=' in x)
   if current.get('ATLAS_PORT')!=str(state['api_port']) or current.get('ATLAS_DB_URL')!=stored['ATLAS_DB_URL']:raise SystemExit('Process identity changed; refusing to stop.')
   os.kill(pid,signal.SIGTERM)
  subprocess.run([str(pg/'pg_ctl'),'-D',str(work/'data'),'-w','stop','-m','fast'],check=True,stdout=subprocess.DEVNULL)
  print('Sandbox stopped; private evidence retained.');raise SystemExit(0)
 order=str(uuid.UUID(state['order_id']))
 e={**os.environ,'PGPASSWORD':stored['ATLAS_BOOTSTRAP_PASSWORD'],'PGOPTIONS':'-c default_transaction_read_only=on'}
 query=f"SELECT payment_status,delivery_status,total_cents FROM atlas_web.orders WHERE id='{order}'; SELECT state,mode FROM atlas_web.payment_attempts WHERE order_id='{order}'; SELECT count(*) AS delivery_obligations FROM atlas_web.delivery_outbox WHERE order_id='{order}';"
 r=subprocess.run([str(pg/'psql'),'-X','-h','127.0.0.1','-p',str(state['db_port']),'-U','atlas_api_bootstrap','-d','postgres','-c',query],env=e,capture_output=True,text=True)
 if r.returncode:raise SystemExit('Sandbox query failed; inspect private state.')
 print(r.stdout);raise SystemExit(0)
if work.exists():raise SystemExit('Sandbox already exists; use --status before preparing another payment.')
values=dict(l.split('=',1) for l in (root/'.env').read_text().splitlines() if '=' in l and not l.startswith('#'))
def remote(path):
 req=urllib.request.Request('https://api.mercadopago.com'+path,headers={'Authorization':'Bearer '+values['ATLAS_MP_ACCESS_TOKEN'],'Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
account=remote('/users/me')
if 'test_user' not in account.get('tags',[]) or str(account['id'])!=values['ATLAS_MP_COLLECTOR_ID'] or account.get('site_id')!='MLB':raise SystemExit('A matching Brazilian test seller is required.')
work.mkdir(mode=0o700)
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
dbport,apiport=port(),port()
env={k:v for k,v in os.environ.items() if not k.startswith(('ATLAS_','SPRING_'))}
env.update({k:values[k] for k in ['ATLAS_MP_ACCESS_TOKEN','ATLAS_MP_WEBHOOK_SECRET','ATLAS_MP_COLLECTOR_ID']})
env.update({'ATLAS_MP_MODE':'test','ATLAS_PAYMENT_ENABLED':'true','ATLAS_SALES_ENABLED':'true','ATLAS_MP_NOTIFICATION_URL':values['ATLAS_MP_NOTIFICATION_URL'],'ATLAS_WEB_URL':'https://www.atlascobblemon.com.br','ATLAS_BOOTSTRAP_PASSWORD':secrets.token_urlsafe(32),'ATLAS_DB_PASSWORD':secrets.token_urlsafe(32),'ATLAS_MIGRATION_PASSWORD':secrets.token_urlsafe(32),'ATLAS_DB_USERNAME':'atlas_api_runtime','ATLAS_MIGRATION_USERNAME':'atlas_api_migrator','ATLAS_DB_URL':f'jdbc:postgresql://127.0.0.1:{dbport}/postgres','ATLAS_MAIL_ENCRYPTION_KEY':base64.b64encode(secrets.token_bytes(32)).decode(),'ATLAS_LOCAL_MAIL_DIRECTORY':str(work/'mail'),'ATLAS_CORE_KEY':secrets.token_urlsafe(32),'ATLAS_PORT':str(apiport),'ATLAS_BIND_ADDRESS':'127.0.0.1','SPRING_PROFILES_ACTIVE':'test'})
state={'db_port':dbport,'api_port':apiport,'work':str(work),'order_id':None}
def save():
 (work/'state.json').write_text(json.dumps(state));(work/'state.json').chmod(0o600)
 (work/'process-env.json').write_text(json.dumps(env));(work/'process-env.json').chmod(0o600)
save()
pw=work/'init-password';pw.write_text(env['ATLAS_BOOTSTRAP_PASSWORD']);pw.chmod(0o600)
subprocess.run([str(pg/'initdb'),'-D',str(work/'data'),'-U','atlas_api_bootstrap','--auth=scram-sha-256','--pwfile',str(pw),'--encoding=UTF8','--no-locale'],check=True,stdout=subprocess.DEVNULL);pw.unlink()
subprocess.run([str(pg/'pg_ctl'),'-D',str(work/'data'),'-w','start','-l',str(work/'postgres.log'),'-o',f'-p {dbport} -h 127.0.0.1 -k {work}'],check=True,stdout=subprocess.DEVNULL)
def sql(query):
 e={**env,'PGPASSWORD':env['ATLAS_BOOTSTRAP_PASSWORD']}
 r=subprocess.run([str(pg/'psql'),'-X','-h','127.0.0.1','-p',str(dbport),'-U','atlas_api_bootstrap','-d','postgres','-v','ON_ERROR_STOP=1','-At'],input=query,text=True,env=e,capture_output=True)
 if r.returncode:raise RuntimeError('Sandbox fixture query failed; private logs require inspection.')
 return r.stdout.strip()
sql((root/'infra/postgres/provision.sql').read_text())
with (work/'api.log').open('a') as log:
 process=subprocess.Popen(['java','-jar',str(root/'target/atlas-api-0.5.0.jar')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
state['api_pid']=process.pid;save()
base=f'http://127.0.0.1:{apiport}';browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
def call(path,body=None,extra=None):
 headers={'Content-Type':'application/json',**(extra or {})}
 if body is not None:
  csrf=call('/api/v1/auth/csrf');headers[csrf['headerName']]=csrf['token']
 req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
 try:
  with browser.open(req,timeout=15) as r:
   raw=r.read();return json.loads(raw) if raw else None
 except urllib.error.HTTPError as e:
  d=json.load(e);raise RuntimeError('Sandbox API: '+str(e.code)+' '+d.get('code','unknown')) from None
for _ in range(90):
 if process.poll() is not None:raise SystemExit('Sandbox API failed; inspect private api.log.')
 try:
  if call('/actuator/health/readiness')['status']=='UP':break
 except (OSError,ValueError,RuntimeError):pass
 time.sleep(1)
else:raise SystemExit('Sandbox API not ready.')
email=uuid.uuid4().hex+'@example.invalid';password=secrets.token_urlsafe(32)
call('/api/v1/auth/register',{'username':'Payment sandbox','email':email,'password':password})
user=call('/api/v1/auth/login',{'email':email,'password':password})['id'];uuid.UUID(user)
# Synthetic fixtures are confined to the freshly initialized private cluster.
sql(f"UPDATE atlas_web.users SET email_verified=TRUE WHERE id='{user}'; INSERT INTO atlas_web.minecraft_links(id,user_id,subject,core_player_id,minecraft_uuid,nickname,server,linked_at) VALUES('{uuid.uuid4()}','{user}','{uuid.uuid4()}',1,'{uuid.uuid4()}','SandboxTest','emerald',now()); UPDATE atlas_web.product_servers SET purchasable=TRUE WHERE server='emerald';")
catalog=call('/api/v1/catalog');product=next(p for p in catalog['products'] if p['category']=='VIPs' and p['durationDays']==30)
order=call('/api/v1/orders/checkout',{'productId':product['id'],'server':'emerald','quantity':1,'productRevision':product['revision'],'catalogRevision':catalog['revision'],'expectedCents':product['finalCents']},{'Idempotency-Key':str(uuid.uuid4())})
state['order_id']=order['id'];save()
checkout=call('/api/v1/orders/'+order['id']+'/payment',{})
state['checkout_url']=checkout['checkoutUrl'];state['expires_at']=order['expiresAt'];state['amount_cents']=order['totalCents'];save()
print(json.dumps({'checkout_url':checkout['checkoutUrl'],'amount_cents':order['totalCents'],'expires_at':order['expiresAt'],'mode':checkout['mode']}))
