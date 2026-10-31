CREATE TABLE IF NOT EXISTS moderation_punishments (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    target_player_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    target_name VARCHAR(32) NOT NULL,
    target_ip VARCHAR(64),
    actor_player_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    actor_name VARCHAR(32) NOT NULL,
    reason TEXT NOT NULL,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by_player_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    revoked_by_name VARCHAR(32),
    revoked_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_moderation_punishments_target
    ON moderation_punishments(target_player_id, type, revoked_at, expires_at);

CREATE INDEX IF NOT EXISTS idx_moderation_punishments_target_name
    ON moderation_punishments(LOWER(target_name));

CREATE INDEX IF NOT EXISTS idx_moderation_punishments_ip
    ON moderation_punishments(target_ip, type, revoked_at, expires_at);

CREATE INDEX IF NOT EXISTS idx_moderation_punishments_created
    ON moderation_punishments(created_at DESC);
