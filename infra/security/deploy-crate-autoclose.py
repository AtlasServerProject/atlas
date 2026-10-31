#!/usr/bin/env python3
"""Install five-second automatic crate result closing with backup and rollback."""
import argparse,datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
ROOT=pathlib.Path('/home/somente/dev/atlas')
SERVER=pathlib.Path('/opt/atlas/server/fabric')
STAGE=ROOT/'infra/releases/atlas-crate-autoclose-1.40.5-crate.3'
VERSION='1.40.5+crate.3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def properties(raw):
    return {s.split('=',1)[0].strip():s.split('=',1)[1].strip() for s in raw.decode().splitlines() if '=' in s and not s.lstrip().startswith(('#','!'))}
def preflight():
    jar=STAGE/f'atlas-core-{VERSION}.jar'
    report=json.loads((STAGE/'verification.json').read_text())
    if sha(jar)!=jar.with_suffix('.jar.sha256').read_text().strip() or sha(jar)!=report['sha256']:
        raise SystemExit('Staged checksum mismatch; no changes made.')
    with zipfile.ZipFile(jar) as z:
        if z.testzip() or json.loads(z.read('fabric.mod.json'))['version']!=VERSION:
            raise SystemExit('Invalid staged release.')
    installed=list((SERVER/'mods').glob('atlas-core-*.jar'))
    if len(installed)!=1:raise SystemExit('Expected exactly one installed Core.')
    old=installed[0]
    if sha(old)==report['sha256']:
        print('Crate auto-close is already installed. No restart needed.');return None
    if old.name!='atlas-core-1.40.5+crate.2.jar' or sha(old)!=report['baseSha256']:
        raise SystemExit('Installed Core differs from the verified base; no changes made.')
    if subprocess.check_output(['systemctl','show','atlas','-p','User','--value'],text=True).strip()!='atlas-minecraft':
        raise SystemExit('Unexpected Minecraft service user.')
    # Verify that no unrelated server code/config was replaced in the hotfix.
    with zipfile.ZipFile(old) as a,zipfile.ZipFile(jar) as b:
        changed=set(report['changedEntries'])
        if set(b.namelist())-set(a.namelist())!= set():
            raise SystemExit('Unexpected archive additions.')
        for n in a.namelist():
            if n not in changed and a.read(n)!=b.read(n):raise SystemExit('Unexpected non-crate change.')
        if any(n!='fabric.mod.json' and not n.startswith(('io/atlas/modules/crates/service/CrateService','io/atlas/modules/crates/service/CrateSpinTimeline','io/atlas/modules/crates/menu/CrateMenu')) for n in changed):
            raise SystemExit('Unexpected hotfix scope.')
    print('Verified auto-close: five seconds after final reward; reel, sounds and delivery preserved.')
    return jar,old

def apply():
    if os.geteuid()!=0:raise SystemExit('sudo required to restart the isolated Minecraft service.')
    checked=preflight()
    if checked is None:return
    jar,old=checked
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=pathlib.Path('/var/backups/atlas-security')/('crate-autoclose-'+stamp)
    backup.mkdir(parents=True,mode=0o700)
    shutil.copy2(old,backup/old.name)
    before=(SERVER/'server.properties').read_bytes()
    owner=old.stat();destination=SERVER/'mods'/jar.name
    rollback=backup/'rollback.py'
    rollback.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,subprocess
if os.geteuid()!=0:raise SystemExit('root required')
p=pathlib.Path(__file__).parent;s=pathlib.Path('/opt/atlas/server/fabric/mods')
subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
(s/'atlas-core-1.40.5+crate.3.jar').unlink(missing_ok=True)
shutil.copy2(p/'atlas-core-1.40.5+crate.2.jar',s/'atlas-core-1.40.5+crate.2.jar')
subprocess.run(['systemctl','start','atlas'],check=True)
print('Previous Core restored. No worlds or rewards edited.')
''')
    rollback.chmod(0o700)
    print('Restarting Minecraft gracefully. No worlds, reward weights or database records are edited.',flush=True)
    try:
        subprocess.run(['systemctl','stop','atlas'],check=True,timeout=180)
        shutil.copy2(jar,destination);os.chown(destination,owner.st_uid,owner.st_gid);destination.chmod(0o644)
        if sha(destination)!=sha(jar):raise RuntimeError('Installed checksum mismatch')
        old.unlink()
        if len(list((SERVER/'mods').glob('atlas-core-*.jar')))!=1:raise RuntimeError('Duplicate Core')
        subprocess.run(['systemctl','start','atlas'],check=True)
        until=time.monotonic()+150
        while time.monotonic()<until:
            log=(SERVER/'logs/latest.log').read_text(errors='replace')
            if subprocess.run(['systemctl','is-active','--quiet','atlas']).returncode==0 and f'atlas-core {VERSION}' in log and 'Done (' in log:break
            time.sleep(2)
        else:raise RuntimeError('Startup health check failed')
        if properties((SERVER/'server.properties').read_bytes())!=properties(before):raise RuntimeError('Server configuration changed unexpectedly')
    except BaseException:
        subprocess.run(['/usr/bin/python3',str(rollback)],check=True);raise
    print('Crate auto-close active. Test one opening in-game. Rollback:',rollback)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true')
    apply() if parser.parse_args().apply else preflight()
