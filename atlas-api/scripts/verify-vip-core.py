#!/usr/bin/env python3
"""Compile the real Core VIP repository and exercise it against a disposable cluster."""
import os,secrets,socket,subprocess,tempfile,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2];core=root/'atlas-core';pg=Path('/usr/lib/postgresql/18/bin');work=Path(tempfile.mkdtemp(prefix='atlas-vip-core-'));work.chmod(0o700)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
password=secrets.token_urlsafe(32);env={**os.environ,'PGPASSWORD':password};pw=work/'pw';pw.write_text(password);pw.chmod(0o600);started=False
try:
 subprocess.run([str(pg/'initdb'),'-D',str(work/'data'),'-U','vip_test','--auth=scram-sha-256','--pwfile',str(pw),'--encoding=UTF8','--no-locale'],check=True,stdout=subprocess.DEVNULL);pw.unlink()
 subprocess.run([str(pg/'pg_ctl'),'-D',str(work/'data'),'-w','start','-l',str(work/'pg.log'),'-o',f'-p {port} -h 127.0.0.1 -k {work}'],check=True,stdout=subprocess.DEVNULL);started=True
 fixture="CREATE ROLE atlas_app; CREATE TABLE players(id BIGINT PRIMARY KEY,uuid UUID UNIQUE NOT NULL,username TEXT NOT NULL);"+(root/'database/migrations/033_site_identities.sql').read_text()+(root/'database/migrations/034_commercial_vip_ledger.sql').read_text()
 subprocess.run([str(pg/'psql'),'-X','-h','127.0.0.1','-p',str(port),'-U','vip_test','-d','postgres','-v','ON_ERROR_STOP=1'],input=fixture,text=True,env=env,check=True,stdout=subprocess.DEVNULL)
 jdbc=next((Path.home()/'.m2/repository/org/postgresql/postgresql').glob('*/postgresql-*.jar'))
 sources=[core/'src/main/java/io/atlas/modules/database/DatabaseConfig.java',core/'src/main/java/io/atlas/modules/vip/model/VipLedger.java',core/'src/main/java/io/atlas/modules/vip/repository/VipRepository.java',core/'src/test/java/io/atlas/modules/vip/VipLedgerTest.java',core/'src/test/java/io/atlas/modules/vip/VipRepositoryTest.java']
 subprocess.run(['javac','-d',str(work/'classes'),*[str(p) for p in sources]],check=True)
 env.update({'ATLAS_VIP_TEST_URL':f'jdbc:postgresql://127.0.0.1:{port}/postgres','ATLAS_VIP_TEST_USER':'vip_test','ATLAS_VIP_TEST_PASSWORD':password,'ATLAS_VIP_TEST_ISOLATED':'yes'})
 for name in ['VipLedgerTest','VipRepositoryTest']:subprocess.run(['java','-cp',str(work/'classes')+':'+str(jdbc),'io.atlas.modules.vip.'+name],env=env,check=True)
finally:
 if started:subprocess.run([str(pg/'pg_ctl'),'-D',str(work/'data'),'-w','stop','-m','fast'],stdout=subprocess.DEVNULL)
 shutil.rmtree(work)
