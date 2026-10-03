package io.atlas.api.auth.repository;

import java.sql.Timestamp;
import java.time.Instant;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class RateLimitRepository {
    private final JdbcClient jdbc;
    public RateLimitRepository(JdbcClient jdbc) { this.jdbc = jdbc; }

    public int increment(String key, Instant now, Instant windowStart) {
        return jdbc.sql("""
            INSERT INTO atlas_web.auth_rate_limits(bucket_key,window_started_at,attempts) VALUES(:key,:now,1)
            ON CONFLICT(bucket_key) DO UPDATE SET
              attempts=CASE WHEN auth_rate_limits.window_started_at<=:start THEN 1 ELSE auth_rate_limits.attempts+1 END,
              window_started_at=CASE WHEN auth_rate_limits.window_started_at<=:start THEN :now ELSE auth_rate_limits.window_started_at END
            RETURNING attempts
            """)
            .param("key", key).param("now", Timestamp.from(now)).param("start", Timestamp.from(windowStart))
            .query(Integer.class).single();
    }
}
