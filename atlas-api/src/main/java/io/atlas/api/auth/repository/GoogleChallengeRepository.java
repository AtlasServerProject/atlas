package io.atlas.api.auth.repository;
import java.time.Instant;import org.springframework.jdbc.core.simple.JdbcClient;import org.springframework.stereotype.Repository;
@Repository public class GoogleChallengeRepository {
 private final JdbcClient db;public GoogleChallengeRepository(JdbcClient db){this.db=db;}
 public void create(String hash,Instant expires){db.sql("INSERT INTO atlas_web.google_login_challenges(nonce_hash,expires_at) VALUES(:hash,:expires)").param("hash",hash).param("expires",java.sql.Timestamp.from(expires)).update();}
 public boolean consume(String hash,Instant now){return db.sql("DELETE FROM atlas_web.google_login_challenges WHERE nonce_hash=:hash AND expires_at>:now").param("hash",hash).param("now",java.sql.Timestamp.from(now)).update()==1;}
}
