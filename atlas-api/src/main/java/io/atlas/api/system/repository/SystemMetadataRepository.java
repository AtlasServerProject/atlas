package io.atlas.api.system.repository;

import java.time.Instant;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class SystemMetadataRepository {
    private final JdbcClient jdbc;
    public SystemMetadataRepository(JdbcClient jdbc) { this.jdbc = jdbc; }
    public Metadata read() {
        return jdbc.sql("SELECT schema_generation, initialized_at FROM atlas_web.system_metadata WHERE id = 1")
            .query((rs, row) -> new Metadata(rs.getInt("schema_generation"), rs.getTimestamp("initialized_at").toInstant())).single();
    }
    public record Metadata(int schemaGeneration, Instant initializedAt) { }
}
