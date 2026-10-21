CREATE TABLE IF NOT EXISTS player_permissions (
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, permission)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON player_permissions TO atlas_app;
