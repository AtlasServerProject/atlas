CREATE TABLE IF NOT EXISTS item_recovery_entries (
    id BIGSERIAL PRIMARY KEY,
    player_uuid UUID NOT NULL,
    source VARCHAR(24) NOT NULL,
    item_snbt TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    recovered_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_item_recovery_available
ON item_recovery_entries(player_uuid, expires_at, recovered_at);
