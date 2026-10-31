#!/usr/bin/env python3
"""Standardize the player-facing lobby name while preserving world identifiers."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas');SERVER=pathlib.Path('/opt/atlas/server/fabric')
STAGE=ROOT/'infra/releases/atlas-lobby-label-1.40.5-lobby.1';VERSION='1.40.5+lobby.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def properties(raw):return {s.split('=',1)[0].strip():s.split('=',1)[1].strip() for s in raw.decode().splitlines() if '=' in s and not s.lstrip().startswith(('#','!'))}
PREFIXES=['io/atlas/commands/LobbyCommand', 'io/atlas/commands/RandomTeleportCommand', 'io/atlas/modules/auth/listener/AuthConnectionListener', 'io/atlas/modules/lobby/service/DevTransferService', 'io/atlas/modules/lobby/service/ServerSelectorService', 'io/atlas/modules/lobby/service/LobbyHudService', 'io/atlas/modules/lobby/service/LobbyTravelService', 'io/atlas/modules/purchases/service/PurchasesService', 'io/atlas/modules/survival/service/SurvivalRulesService', 'io/atlas/modules/survival/service/RandomTeleportService', 'io/atlas/modules/survival/listener/SurvivalRespawnListener', 'io/atlas/modules/warp/service/WarpService']
def allowed(n):return n=='fabric.mod.json' or any(n==p+'.class' or n.startswith(p+'$') and n.endswith('.class') for p in PREFIXES)
def preflight():
    jar=STAGE/f'atlas-core-{VERSION}.jar';report=json.loads((STAGE/'verification.json').read_text())
    if sha(jar)!=report['sha256'] or sha(jar)!=jar.with_suffix('.jar.sha256').read_text().strip():raise SystemExit('Staged checksum mismatch.')
    installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
    if len(installed)!=1:raise SystemExit('Expected exactly one installed Atlas Core.')
    old=installed[0]
    if sha(old)==report['sha256']:print('Lobby naming already installed. No restart needed.');return None
    if old.name!='atlas-core-1.40.5+warp.1.jar' or sha(old)!=report['baseSha256']:raise SystemExit('Installed Core differs from verified base; no changes made.')
    with zipfile.ZipFile(old) as a,zipfile.ZipFile(jar) as b:
        if b.testzip() is not None or json.loads(b.read('fabric.mod.json'))['version']!=VERSION:raise SystemExit('Invalid staged archive.')
        if not set(a.namelist()).issubset(b.namelist()):raise SystemExit('Unexpected removed archive entries.')
        for n in b.namelist():
            if n not in a.namelist() or a.read(n)!=b.read(n):
                if not allowed(n):raise SystemExit('Unexpected non-warp code change.')
    if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':raise SystemExit('Unexpected Minecraft service user.')
    print('Verified Lobby naming: internal world IDs, destinations and crate fixes preserved.')
    return jar,old

def apply():
    if os.geteuid()!=0:raise SystemExit('sudo required to restart the isolated Minecraft service.')
    checked=preflight()
    if checked is None:return
    warpfile=SERVER/'config/atlas/warps.json'
    if warpfile.exists():
        current=json.loads(warpfile.read_text())
        if any(w['name']=='emerald' for w in current['warps']) and any(w['name']=='lobby' for w in current['warps']):raise SystemExit('Both emerald and lobby warps exist; no changes made.')
    jar,old=checked;stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=pathlib.Path('/var/backups/atlas-security')/('lobby-name-'+stamp);backup.mkdir(parents=True,mode=0o700)
    shutil.copy2(old,backup/old.name);before=(SERVER/'server.properties').read_bytes()
    owner=old.stat();destination=SERVER/'mods'/jar.name
    snapshots={}
    for name in ['warps.json','warps.json.bak']:
        config=SERVER/'config/atlas'/name
        if config.exists():
            meta=config.stat();shutil.copy2(config,backup/name);snapshots[name]={'uid':meta.st_uid,'gid':meta.st_gid}
        else:snapshots[name]=None
    (backup/'config-snapshots.json').write_text(json.dumps(snapshots))
    rollback=backup/'rollback.py';rollback.write_text('''#!/usr/bin/env python3
import json,os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'mods/atlas-core-1.40.5+lobby.1.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.40.5+warp.1.jar',s/'mods/atlas-core-1.40.5+warp.1.jar')
for name,meta in json.loads((p/'config-snapshots.json').read_text()).items():
    dest=s/'config/atlas'/name
    if meta is None:dest.unlink(missing_ok=True)
    else:
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p/name,dest);os.chown(dest,meta['uid'],meta['gid'])
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core and warp config restored. Worlds, accounts and rewards untouched.')
''');rollback.chmod(0o700)
    print('Restarting Minecraft gracefully; no world edits or database migration.',flush=True)
    try:
        subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
        shutil.copy2(jar,destination);os.chown(destination,owner.st_uid,owner.st_gid);destination.chmod(0o644)
        if sha(destination)!=sha(jar):raise RuntimeError('Copy checksum mismatch')
        if warpfile.exists():
            import uuid
            doc=json.loads(warpfile.read_text());meta=warpfile.stat();changed=False
            for warp in doc['warps']:
                if warp['name']=='emerald':
                    warp['name']='lobby';warp['title']='Lobby';warp['revision']=str(uuid.uuid4());changed=True
                elif warp.get('title')=='Lobby Emerald':warp['title']='Lobby';changed=True
            if changed:
                temp=warpfile.with_name('warps.rename.tmp')
                with temp.open('w') as f:json.dump(doc,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
                os.chown(temp,meta.st_uid,meta.st_gid);temp.chmod(0o600)
                shutil.copy2(warpfile,warpfile.with_suffix('.json.bak'));os.chown(warpfile.with_suffix('.json.bak'),meta.st_uid,meta.st_gid)
                temp.replace(warpfile)
        old.unlink()
        if len(list((SERVER/'mods').glob('atlas-core-*.jar')))!=1:raise RuntimeError('Duplicate Core')
        subprocess.run(['systemctl','start','atlas'],check=True)
        until=time.monotonic()+150
        while time.monotonic()<until:
            log=(SERVER/'logs/latest.log').read_text(errors='replace')
            if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and f'atlas-core {VERSION}' in log and 'Warps Atlas:' in log and 'Done (' in log:break
            time.sleep(2)
        else:raise RuntimeError('Startup health check failed')
        if properties((SERVER/'server.properties').read_bytes())!=properties(before):raise RuntimeError('Unexpected server configuration change')
    except BaseException:
        subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
    print('Lobby naming active. Use /lobby and /warp lobby. Rollback:',rollback)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true')
    apply() if parser.parse_args().apply else preflight()
