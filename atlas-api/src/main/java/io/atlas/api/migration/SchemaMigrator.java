package io.atlas.api.migration;
/** Operator-only entry point: no web server, schedules, provider requests or application login. */
public final class SchemaMigrator {
 private SchemaMigrator(){}
 public static void main(String[] args){
  String url=System.getenv("ATLAS_DB_URL"),user=System.getenv("ATLAS_MIGRATION_USERNAME"),password=System.getenv("ATLAS_MIGRATION_PASSWORD");
  if(!"jdbc:postgresql://127.0.0.1:55432/atlas_api_local".equals(url)||!"atlas_api_migrator".equals(user)||password==null||password.isBlank())throw new IllegalStateException("Explicit primary API migration configuration required");
  var result=org.flywaydb.core.Flyway.configure().dataSource(url,user,password).defaultSchema("atlas_web").schemas("atlas_web").locations("classpath:db/migration").cleanDisabled(true).validateOnMigrate(true).load().migrate();
  System.out.println("Atlas schema migration completed: "+result.migrationsExecuted+" migration(s).");
 }
}
