package io.atlas.api.auth.repository;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
@Repository
public class TokenRepository {
    private final JdbcClient jdbc;
    public TokenRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    public void create(UUID user,String hash,String purpose,Instant expiry) {
        jdbc.sql("INSERT INTO atlas_web.auth_tokens(id,user_id,token_hash,purpose,expires_at) VALUES(:id,:user,:hash,:purpose,:expiry)")
            .param("id",UUID.randomUUID()).param("user",user).param("hash",hash).param("purpose",purpose).param("expiry",java.sql.Timestamp.from(expiry)).update();
    }
    public Optional<UUID> owner(String hash,String purpose) {
        return jdbc.sql("SELECT user_id FROM atlas_web.auth_tokens WHERE token_hash=:hash AND purpose=:purpose").param("hash",hash).param("purpose",purpose).query(UUID.class).optional();
    }
    public boolean consume(String hash,String purpose,Instant now) {
        return jdbc.sql("UPDATE atlas_web.auth_tokens SET used_at=:now WHERE token_hash=:hash AND purpose=:purpose AND used_at IS NULL AND expires_at > :now")
            .param("hash",hash).param("purpose",purpose).param("now",java.sql.Timestamp.from(now)).update()==1;
    }
    public void invalidate(UUID user,String purpose,Instant now) {
        jdbc.sql("UPDATE atlas_web.auth_tokens SET used_at=:now WHERE user_id=:user AND purpose=:purpose AND used_at IS NULL")
            .param("user",user).param("purpose",purpose).param("now",java.sql.Timestamp.from(now)).update();
    }
}
