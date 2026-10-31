package io.atlas.api.auth.repository;
import java.util.*;import java.time.Instant;import org.springframework.jdbc.core.simple.JdbcClient;import org.springframework.stereotype.Repository;
@Repository public class RecoveryEmailRepository {
 public record Entry(String email,String pending,String hash,Instant expires,int attempts){}
 private final JdbcClient db;public RecoveryEmailRepository(JdbcClient db){this.db=db;}
 public Optional<String> email(UUID player){return db.sql("SELECT email FROM atlas_web.minecraft_recovery_email WHERE minecraft_uuid=:p AND email IS NOT NULL AND verified_at IS NOT NULL").param("p",player).query(String.class).optional();}
 public void pending(UUID player,String email,String hash,Instant expires){db.sql("INSERT INTO atlas_web.minecraft_recovery_email(minecraft_uuid,pending_email,code_hash,expires_at) VALUES(:p,:e,:h,:x) ON CONFLICT(minecraft_uuid) DO UPDATE SET pending_email=:e,code_hash=:h,expires_at=:x,attempts=0").param("p",player).param("e",email).param("h",hash).param("x",java.sql.Timestamp.from(expires)).update();}
 public Optional<Entry> lock(UUID player){return db.sql("SELECT email,pending_email,code_hash,expires_at,attempts FROM atlas_web.minecraft_recovery_email WHERE minecraft_uuid=:p FOR UPDATE").param("p",player).query((r,n)->new Entry(r.getString(1),r.getString(2),r.getString(3),r.getTimestamp(4)==null?null:r.getTimestamp(4).toInstant(),r.getInt(5))).optional();}
 public void attempt(UUID player){db.sql("UPDATE atlas_web.minecraft_recovery_email SET attempts=attempts+1 WHERE minecraft_uuid=:p").param("p",player).update();}
 public void confirm(UUID player){db.sql("UPDATE atlas_web.minecraft_recovery_email SET email=pending_email,verified_at=CURRENT_TIMESTAMP,pending_email=NULL,code_hash=NULL,expires_at=NULL,attempts=0 WHERE minecraft_uuid=:p").param("p",player).update();}
 public void invalidateReset(UUID player){db.sql("UPDATE atlas_web.minecraft_password_recovery SET consumed=true WHERE minecraft_uuid=:p").param("p",player).update();}
}
