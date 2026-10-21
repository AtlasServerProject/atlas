CREATE TABLE IF NOT EXISTS legendary_scheduler (
 id INTEGER PRIMARY KEY CHECK(id=1), last_attempt BIGINT NOT NULL DEFAULT 0,
 next_attempt BIGINT NOT NULL, warned BOOLEAN NOT NULL DEFAULT FALSE,
 enabled BOOLEAN NOT NULL, missed_cycles BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS legendary_attempts (
 id UUID PRIMARY KEY, attempted_at BIGINT NOT NULL, kind TEXT NOT NULL,
 outcome TEXT NOT NULL, detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS legendary_events (
 id UUID PRIMARY KEY REFERENCES legendary_attempts(id), pokemon_uuid UUID NOT NULL UNIQUE,
 entity_uuid UUID NOT NULL UNIQUE, species TEXT NOT NULL, dimension TEXT NOT NULL,
 biome TEXT NOT NULL, x DOUBLE PRECISION NOT NULL, y DOUBLE PRECISION NOT NULL,
 z DOUBLE PRECISION NOT NULL, created_at BIGINT NOT NULL, expires_at BIGINT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','ACTIVE','CAPTURED','DEFEATED','DESPAWNED','FAILED','LOST')),
 trainer_uuid UUID, finished_at BIGINT, test BOOLEAN NOT NULL DEFAULT FALSE,
 capture_data JSONB, announcement_sent BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS legendary_events_status ON legendary_events(status);
GRANT SELECT,INSERT,UPDATE ON legendary_scheduler,legendary_attempts,legendary_events TO atlas_app;
