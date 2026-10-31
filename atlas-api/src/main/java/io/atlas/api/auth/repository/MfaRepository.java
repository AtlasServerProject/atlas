package io.atlas.api.auth.repository;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
@Repository public class MfaRepository {
 public record State(String secret,String pending,Instant expires,Instant enabled,long last){}
 private final JdbcTemplate db;
 public MfaRepository(JdbcTemplate db){this.db=db;}
 public State lock(UUID id){
  db.queryForObject("SELECT id FROM atlas_web.users WHERE id=? FOR UPDATE",UUID.class,id);
  return db.query("SELECT * FROM atlas_web.account_mfa WHERE user_id=? FOR UPDATE",(r,n)->new State(r.getString("secret_ciphertext"),r.getString("pending_ciphertext"),r.getTimestamp("pending_expires_at")==null?null:r.getTimestamp("pending_expires_at").toInstant(),r.getTimestamp("enabled_at")==null?null:r.getTimestamp("enabled_at").toInstant(),r.getLong("last_step")),id).stream().findFirst().orElse(null);
 }
 public void pending(UUID id,String ciphertext,Instant expires){db.update("INSERT INTO atlas_web.account_mfa(user_id,pending_ciphertext,pending_expires_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET pending_ciphertext=EXCLUDED.pending_ciphertext,pending_expires_at=EXCLUDED.pending_expires_at WHERE account_mfa.enabled_at IS NULL",id,ciphertext,java.sql.Timestamp.from(expires));}
 public void enable(UUID id,long step,Instant now){db.update("UPDATE atlas_web.account_mfa SET secret_ciphertext=pending_ciphertext,pending_ciphertext=NULL,pending_expires_at=NULL,enabled_at=?,last_step=? WHERE user_id=?",java.sql.Timestamp.from(now),step,id);db.update("UPDATE atlas_web.users SET mfa_enabled=true,auth_version=auth_version+1 WHERE id=?",id);db.update("DELETE FROM atlas_web.web_sessions WHERE principal_name=?",id.toString());}
 public void step(UUID id,long step){db.update("UPDATE atlas_web.account_mfa SET last_step=? WHERE user_id=?",step,id);}
 public void recovery(UUID id,String hash){db.update("INSERT INTO atlas_web.mfa_recovery_codes(user_id,code_hash) VALUES(?,?)",id,hash);}
 public boolean consume(UUID id,String hash){return db.update("DELETE FROM atlas_web.mfa_recovery_codes WHERE user_id=? AND code_hash=?",id,hash)==1;}
}
