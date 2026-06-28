CREATE TABLE player_sessions (
    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    ip_address VARCHAR(60),

    logged_in BOOLEAN NOT NULL DEFAULT FALSE,

    login_at TIMESTAMP DEFAULT NOW(),

    expires_at TIMESTAMP
);

CREATE INDEX idx_sessions_player ON player_sessions(player_id);
CREATE INDEX idx_sessions_logged ON player_sessions(logged_in);