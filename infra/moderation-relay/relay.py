#!/usr/bin/env python3
"""Durable moderation journal and Discord delivery, without a Gateway session."""
import os,json,time,sqlite3,hashlib,re,unicodedata,urllib.request,urllib.error,subprocess
from pathlib import Path
from datetime import datetime,timezone
import psycopg
HOME=Path.home(); ROOT=HOME/'dev/atlas'; STATE=HOME/'.local/share/atlas-moderation-relay/state.sqlite3'
CHANNEL='1562967588735295550'

def category(reason):
 text=''.join(c for c in unicodedata.normalize('NFKD',reason.lower()) if not unicodedata.combining(c))
 for name,pattern in [('Flood/spam',r'flood|spam'),('Desrespeito à staff',r'desrespeito.*staff'),('Ofensa',r'ofensa|desrespeito'),('Preconceito',r'preconceito|racismo|xenofobia'),('Conteúdo impróprio',r'improprio'),('Assédio',r'assedio'),('Abuso de bugs',r'bug'),('Modificações ilegais',r'cheat|hack|modificac'),('Divulgação',r'divulgacao(?!.*pesso)'),('Antijogo',r'anti.?jogo'),('Griefing',r'grief'),('Roubo',r'roubo'),('Má utilização de chats',r'utilizacao.*chat')]:
  if re.search(pattern,text):return name
 return text.strip() or 'Motivo não informado'

class Journal:
 def __init__(self,path):
  self.db=sqlite3.connect(path);self.db.executescript('''PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,platform TEXT NOT NULL,target TEXT NOT NULL,category TEXT NOT NULL,punitive INTEGER NOT NULL,occurred TEXT NOT NULL,payload TEXT NOT NULL,delivered INTEGER NOT NULL DEFAULT 0);
  CREATE INDEX IF NOT EXISTS occurrence_idx ON events(platform,target,category,punitive);
  PRAGMA user_version=1;''')
 def get(self,key):
  row=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone();return row[0] if row else None
 def set(self,key,value):self.db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,str(value)));self.db.commit()
 def add(self,e,baseline=False):
  with self.db:self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?)',(e['id'],e['platform'],e['target'],category(e['reason']),int(e['punitive']),e['date'],json.dumps(e),int(baseline)))
 def pending(self):return self.db.execute('SELECT id,payload FROM events WHERE delivered=0 ORDER BY occurred,id LIMIT 20').fetchall()
 def occurrence(self,e):return self.db.execute('SELECT count(*) FROM events WHERE platform=? AND target=? AND category=? AND punitive=1 AND (occurred<? OR (occurred=? AND id<=?))',(e['platform'],e['target'],category(e['reason']),e['date'],e['date'],e['id'])).fetchone()[0]

def api(method,path,body=None):
 data=None if body is None else json.dumps(body).encode();req=urllib.request.Request('https://discord.com/api/v10'+path,data=data,method=method,headers={'Authorization':'Bot '+os.environ['DISCORD_TOKEN'],'Content-Type':'application/json','User-Agent':'AtlasModerationRelay/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
 except urllib.error.HTTPError as error:
  if error.code==429:
   try: delay=float(json.load(error).get('retry_after',5))
   except Exception: delay=5
   time.sleep(min(delay,60))
  raise RuntimeError('Discord HTTP '+str(error.code)) from None

def connection():
 props={}
 p=Path('/opt/atlas/server/fabric/config/atlas-database.properties')
 if p.exists():
  for line in p.read_text().splitlines():
   if '=' in line and not line.lstrip().startswith('#'):
    k,v=line.split('=',1);props[k.strip()]=v.strip()
 return psycopg.connect(host=props.get('host','localhost'),port=props.get('port','5432'),dbname=props.get('database','atlas'),user=props.get('user','atlas_app'),password=props.get('password','atlas'),connect_timeout=10)

def minecraft(j):
 baseline=j.get('minecraft_initialized') is None
 with connection() as db:
  with db.cursor() as c:
   c.execute('SELECT id,type,target_player_id,target_name,actor_name,reason,created_at,expires_at,revoked_at FROM moderation_punishments ORDER BY created_at,id')
   for id,kind,player,name,actor,reason,created,expires,revoked in c:
    e=dict(id=f'mc:{id}',platform='Minecraft',target=str(player) if player else 'ip:'+hashlib.sha256((name or '').encode()).hexdigest(),name=name if player else 'Alvo por IP (oculto)',actor=actor,reason=reason or '',action=kind,date=created.isoformat(),end=expires.isoformat() if expires else None,punitive=True)
    j.add(e,baseline)
    if revoked:j.add(dict(e,id=f'mc-revoke:{id}',action='REVOGAÇÃO '+kind,punitive=False,date=revoked.isoformat()),baseline)
 if baseline:j.set('minecraft_initialized',1)

def discord(j):
 guild=os.environ['DISCORD_GUILD_ID'];cursor=j.get('discord_cursor');baseline=cursor is None
 # Bootstrap counts from Discord's retained audit history without reposting old events.
 before=None;all_entries=[]
 for _ in range(100):
  path=f'/guilds/{guild}/audit-logs?limit=100'+('&before='+before if before else '')
  entries=api('GET',path)['audit_log_entries']
  entries=[e for e in entries if baseline or int(e['id'])>int(cursor)]
  if not entries:break
  all_entries.extend(entries);before=min(entries,key=lambda e:int(e['id']))['id']
  if len(entries)<100:break
 else:raise RuntimeError('Auditoria muito extensa; cursor preservado')
 for entry in sorted(all_entries,key=lambda e:int(e['id'])):
  kind=entry['action_type'];action={20:'KICK',22:'BAN',23:'UNBAN'}.get(kind);end=None;punitive=kind!=23
  if kind==24:
   change=next((x for x in entry.get('changes',[]) if x['key']=='communication_disabled_until'),None)
   if change:
    end=change.get('new_value');action='TIMEOUT' if end else 'TIMEOUT REMOVIDO';punitive=bool(end)
  if not action:continue
  target=entry.get('target_id')
  if not target:continue
  date=datetime.fromtimestamp(((int(entry['id'])>>22)+1420070400000)/1000,timezone.utc).isoformat()
  j.add(dict(id='dc:'+entry['id'],platform='Discord',target=target,name='ID '+target,actor='ID '+str(entry.get('user_id') or 'não informado'),reason=entry.get('reason') or 'Motivo não informado',action=action,date=date,end=end,punitive=punitive),baseline)
 if all_entries:j.set('discord_cursor',max(int(e['id']) for e in all_entries))
 elif baseline:j.set('discord_cursor',((int(time.time()*1000)-1420070400000)<<22))

def activity(j,directory=None):
 directory=Path(directory or '/opt/atlas/server/fabric/logs/atlas-activity')
 for path in sorted(directory.glob('*.jsonl')):
  key='activity_offset:'+path.name
  offset=int(j.get(key) or 0)
  with path.open('rb') as f:
   f.seek(offset)
   for _ in range(1000):
    line=f.readline()
    if not line or not line.endswith(b'\n'):break
    e=json.loads(line)
    row=dict(id='activity:'+e['id'],platform='Minecraft',target=e['uuid'],name=e['actor'],actor=e['actor'],reason=e['text'],action=e['kind'],date=e['date'],end=None,punitive=False,log=True,channel=e['channel'])
    j.add(row)
    j.set(key,f.tell())

def legendary(j,directory=None):
 directory=Path(directory or '/opt/atlas/server/fabric/logs/atlas-legendary-events')
 for path in sorted(directory.glob('*.jsonl')):
  key='legendary_offset:'+path.name
  offset=int(j.get(key) or 0)
  with path.open('rb') as f:
   f.seek(offset)
   for _ in range(1000):
    line=f.readline()
    if not line or not line.endswith(b'\n'):break
    e=json.loads(line)
    row=dict(id='legendary:'+e['id'],platform='Minecraft',target='legendary',name='Atlas',actor='Servidor',reason=e['kind'],action=e['kind'],date=e['date'],end=None,punitive=False,webhook=e['payload'])
    j.add(row)
    j.set(key,f.tell())

def execute_legendary_webhook(payload):
 secret=json.loads((HOME/'.config/atlas/legendary-webhook.json').read_text())
 # Endpoint is constructed locally: no credentials in logs or exception messages.
 endpoint='https://discord.com/api/v10/webhooks/'+secret['id']+'/'+secret['token']+'?wait=true'
 request=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'AtlasLegendaryWebhook/1.0'},method='POST')
 try:
  with urllib.request.urlopen(request,timeout=25) as response:return json.load(response)
 except urllib.error.HTTPError as error:
  if error.code==429:
   try: delay=float(json.load(error).get('retry_after',5))
   except Exception: delay=5
   time.sleep(min(delay,60))
  raise RuntimeError('Webhook HTTP '+str(error.code)) from None

def deliver(j):
 for id,payload in j.pending():
  e=json.loads(payload)
  if e.get('webhook'):
   execute_legendary_webhook(e['webhook'])
   with j.db:j.db.execute('UPDATE events SET delivered=1 WHERE id=?',(id,))
   continue
  count=j.occurrence(e)
  desc=[f"**Jogador:** {e['name']}",f"**Ação:** {e['action']}",f"**Responsável:** {e['actor']}",f"**Motivo:** {e['reason'][:700]}",f"**Infração:** {category(e['reason'])[:200]}",f"**Data:** {e['date']}"]
  if e.get('log'):desc=[f"**Jogador/fonte:** {e['name']}",f"**UUID:** {e['target']}",f"**Evento:** {e['action']}",f"**Origem:** {e['channel']}",f"**Conteúdo:** {e['reason'][:1800]}",f"**Data:** {e['date']}"]
  if e['end']:desc.append('**Até:** '+e['end'])
  if e['punitive']:desc.append(f'**Ocorrência nesta infração:** {count}')
  elif not e.get('log'):desc.append('Revogação — não soma ocorrência.')
  nonce=str(int.from_bytes(hashlib.sha256(id.encode()).digest()[:8],'big'))
  destination='1563004711898980374' if e.get('log') else CHANNEL
  api('POST',f'/channels/{destination}/messages',{'embeds':[{'title':('Atividade • ' if e.get('log') else 'Registro de moderação • ')+e['platform'],'description':'\n'.join(desc),'color':16744295,'footer':{'text':id}}],'allowed_mentions':{'parse':[]},'nonce':nonce,'enforce_nonce':True})
  with j.db:j.db.execute('UPDATE events SET delivered=1 WHERE id=?',(id,))

def main():
 os.umask(0o077);STATE.parent.mkdir(parents=True,exist_ok=True)
 # Parse existing private dotenv with Node, never echo credentials.
 code="import{readFileSync}from'node:fs';import{parseEnv}from'node:util';process.stdout.write(JSON.stringify(parseEnv(readFileSync(process.argv[1],'utf8'))));"
 env=json.loads(subprocess.check_output([str(HOME/'.local/bin/node'),'--input-type=module','-e',code,str(HOME/'.config/atlas/discord-bot.env')],text=True));os.environ.update(env)
 j=Journal(STATE)
 while True:
  for label,fn in [('Minecraft',minecraft),('Discord',discord),('Atividade',activity),('Lendários',legendary),('Entrega',deliver)]:
   try:fn(j)
   except Exception as e:print(label+': falha temporária ('+type(e).__name__+'); nova tentativa em 20s.',flush=True)
  if os.environ.get('ATLAS_RELAY_ONCE')=='1':break
  time.sleep(20)
if __name__=='__main__':main()
