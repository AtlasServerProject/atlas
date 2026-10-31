#!/usr/bin/env python3
"""Exercise production Core identity repositories against the harness's disposable PostgreSQL only."""
import os,subprocess,tempfile,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]
url=os.environ['ATLAS_TEST_DB_URL'];password=os.environ['ATLAS_TEST_ADMIN_PASSWORD']
if not url.startswith('jdbc:postgresql://127.0.0.1:') or not os.environ.get('ATLAS_CORE_TEST_ISOLATED')=='yes':
 raise SystemExit('Only the private disposable test cluster is permitted.')
# Use a separate database on that cluster; never connect to the game database.
base=url.removeprefix('jdbc:');hostport=base.split('/')[2];port=hostport.split(':')[1]
env={**os.environ,'PGPASSWORD':password}
def sql(statement,database='postgres'):
 subprocess.run(['/usr/lib/postgresql/18/bin/psql','-h','127.0.0.1','-p',port,'-U','atlas_api_bootstrap','-d',database,'-v','ON_ERROR_STOP=1','-q'],input=statement,text=True,env=env,stdout=subprocess.DEVNULL,check=True)
sql('CREATE ROLE atlas_app; CREATE DATABASE core_identity_isolated;')
for p in sorted((root/'database/migrations').glob('*.sql')):sql(p.read_text(),'core_identity_isolated')
with tempfile.TemporaryDirectory(prefix='atlas-core-identity-') as temp:
 work=Path(temp);work.chmod(0o700);out=work/'classes';out.mkdir()
 stub=work/'DatabaseManager.java';stub.write_text('''package io.atlas.modules.database; import java.sql.*; public class DatabaseManager { public static Connection connection; public static Connection getConnection(){return connection;} }''')
 test=work/'CoreIdentityTest.java';test.write_text('''import java.util.*; import java.sql.*; import java.nio.charset.StandardCharsets; import io.atlas.modules.database.DatabaseManager; import io.atlas.modules.player.repository.PlayerRepository; import io.atlas.modules.site.repository.SiteRepository;
public class CoreIdentityTest {
 static void require(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 static long count(Connection c,String sql)throws Exception{try(var s=c.createStatement();var r=s.executeQuery(sql)){r.next();return r.getLong(1);}}
 public static void main(String[] args)throws Exception{try(var c=DriverManager.getConnection(System.getenv("CORE_ISOLATED_URL"),"atlas_api_bootstrap",System.getenv("ATLAS_TEST_ADMIN_PASSWORD"))){DatabaseManager.connection=c;var players=new PlayerRepository();var site=new SiteRepository();
 var username="OfflineTest";var offline=UUID.nameUUIDFromBytes(("OfflinePlayer:"+username).getBytes(StandardCharsets.UTF_8));var premium=UUID.randomUUID();players.create(offline,username);var first=site.identity(offline);require(site.identity(offline).subject().equals(first.subject()),"subject is stable");players.promotePremiumIdentity(premium,username);var promoted=site.identity(premium);require(promoted.subject().equals(first.subject()),"UUID promotion preserves website recipient");require(promoted.playerId()==first.playerId(),"canonical player retained");players.updateLogin(premium,"ChangedNick");require(site.identity(premium).subject().equals(first.subject()),"nickname change preserves recipient");
 username="MergeTest";offline=UUID.nameUUIDFromBytes(("OfflinePlayer:"+username).getBytes(StandardCharsets.UTF_8));premium=UUID.randomUUID();players.create(offline,username);players.create(premium,username);var source=site.identity(offline);players.promotePremiumIdentity(premium,username);var merged=site.identity(premium);require(merged.subject().equals(source.subject()),"merge follows canonical players row");require(merged.playerId()!=source.playerId(),"recipient transferred to existing Premium row");
 username="ConflictTest";offline=UUID.nameUUIDFromBytes(("OfflinePlayer:"+username).getBytes(StandardCharsets.UTF_8));premium=UUID.randomUUID();players.create(offline,username);players.create(premium,username);var before=site.identity(offline);var official=site.identity(premium);var rejected=false;try{players.promotePremiumIdentity(premium,username);}catch(RuntimeException expected){rejected=true;}require(rejected,"two site identities need review");require(site.identity(offline).subject().equals(before.subject()),"failed merge preserves Offline account");require(site.identity(premium).subject().equals(official.subject()),"failed merge preserves Premium account");require(c.getAutoCommit(),"transaction restored");System.out.println("PASS: stable site subject, nickname change, Premium promotion, canonical merge and conflict rollback.");}}
}''')
 driver=next((Path.home()/'.m2/repository/org/postgresql/postgresql').glob('*/postgresql-*.jar'))
 sources=[stub,test,root/'atlas-core/src/main/java/io/atlas/modules/player/model/PlayerProfile.java',root/'atlas-core/src/main/java/io/atlas/modules/player/repository/PlayerRepository.java',root/'atlas-core/src/main/java/io/atlas/modules/site/repository/SiteRepository.java']
 subprocess.run(['javac','--release','21','-cp',str(driver),'-d',str(out),*[str(p) for p in sources]],check=True)
 run_env={**env,'CORE_ISOLATED_URL':f'jdbc:postgresql://127.0.0.1:{port}/core_identity_isolated'}
 subprocess.run(['java','-cp',str(out)+':'+str(driver),'CoreIdentityTest'],env=run_env,check=True)
