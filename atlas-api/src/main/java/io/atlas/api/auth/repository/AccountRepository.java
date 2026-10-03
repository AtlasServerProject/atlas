package io.atlas.api.auth.repository;
import io.atlas.api.auth.model.Account;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
@Repository
public class AccountRepository {
    private final JdbcClient jdbc;
    public AccountRepository(JdbcClient jdbc) { this.jdbc=jdbc; }
    private Account map(ResultSet r, int row) throws SQLException {
        return new Account(r.getObject("id",UUID.class),r.getString("username"),r.getString("email"),r.getString("password_hash"),r.getString("role"),r.getBoolean("email_verified"),r.getLong("auth_version"),r.getTimestamp("created_at").toInstant());
    }
    public Optional<Account> email(String email) { return jdbc.sql("SELECT * FROM atlas_web.users WHERE email=:email").param("email",email).query(this::map).optional(); }
    public Optional<Account> id(UUID id) { return jdbc.sql("SELECT * FROM atlas_web.users WHERE id=:id").param("id",id).query(this::map).optional(); }
    public Optional<Account> create(String username,String email,String hash,Instant now) {
        return jdbc.sql("INSERT INTO atlas_web.users(id,username,email,password_hash,created_at) VALUES(:id,:name,:email,:hash,:now) ON CONFLICT(email) DO NOTHING RETURNING *")
            .param("id",UUID.randomUUID()).param("name",username).param("email",email).param("hash",hash).param("now",java.sql.Timestamp.from(now)).query(this::map).optional();
    }
    public void lock(UUID id) { jdbc.sql("SELECT id FROM atlas_web.users WHERE id=:id FOR UPDATE").param("id",id).query(UUID.class).single(); }
    public void verify(UUID id) { jdbc.sql("UPDATE atlas_web.users SET email_verified=true WHERE id=:id").param("id",id).update(); }
    public void password(UUID id,String hash) { jdbc.sql("UPDATE atlas_web.users SET password_hash=:hash,auth_version=auth_version+1 WHERE id=:id").param("hash",hash).param("id",id).update(); }
    public void removeSessions(UUID id) { jdbc.sql("DELETE FROM atlas_web.web_sessions WHERE principal_name=:id").param("id",id.toString()).update(); }
}
