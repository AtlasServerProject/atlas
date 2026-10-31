package io.atlas.api.auth.repository;
import java.util.*;import java.time.Instant;import org.springframework.jdbc.core.simple.JdbcClient;import org.springframework.stereotype.Repository;
@Repository public class MinecraftRecoveryRepository {
 public record Recipient(UUID link,UUID user,String email){}
 public record Challenge(String hash,Instant expires,int attempts,boolean consumed,UUID link,String email){}
 private final JdbcClient db;public MinecraftRecoveryRepository(JdbcClient db){this.db=db;}
 public Optional<Recipient> recipient(UUID player){return db.sql("SELECT l.id,l.user_id,u.email FROM atlas_web.minecraft_links l JOIN atlas_web.users u ON u.id=l.user_id WHERE l.minecraft_uuid=:player AND l.revoked_at IS NULL AND u.email_verified=true ORDER BY l.linked_at DESC LIMIT 1 FOR UPDATE OF l").param("player",player).query((r,n)->new Recipient(r.getObject(1,UUID.class),r.getObject(2,UUID.class),r.getString(3))).optional();}
 public void save(UUID player,UUID link,String email,String hash,Instant expires){db.sql("INSERT INTO atlas_web.minecraft_password_recovery(minecraft_uuid,link_id,recovery_email,code_hash,expires_at) VALUES(:p,:l,:email,:h,:e) ON CONFLICT(minecraft_uuid) DO UPDATE SET link_id=:l,recovery_email=:email,code_hash=:h,expires_at=:e,attempts=0,consumed=false").param("p",player).param("l",link).param("email",email).param("h",hash).param("e",java.sql.Timestamp.from(expires)).update();}
 public Optional<Challenge> lock(UUID player){return db.sql("SELECT code_hash,expires_at,attempts,consumed,link_id,recovery_email FROM atlas_web.minecraft_password_recovery WHERE minecraft_uuid=:p FOR UPDATE").param("p",player).query((r,n)->new Challenge(r.getString(1),r.getTimestamp(2).toInstant(),r.getInt(3),r.getBoolean(4),r.getObject(5,UUID.class),r.getString(6))).optional();}
 public void attempt(UUID player,boolean success){db.sql("UPDATE atlas_web.minecraft_password_recovery SET attempts=attempts+1,consumed=:success WHERE minecraft_uuid=:p").param("p",player).param("success",success).update();}
}
