CREATE TABLE IF NOT EXISTS survival_positions (
    player_id BIGINT PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    yaw REAL NOT NULL,
    pitch REAL NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_survival_positions_updated_at
ON survival_positions(updated_at);
