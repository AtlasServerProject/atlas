CREATE TABLE IF NOT EXISTS players (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    username VARCHAR(32) NOT NULL,
    first_login TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    playtime_seconds BIGINT NOT NULL DEFAULT 0,
    is_online BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_uuid ON players(uuid);
CREATE INDEX IF NOT EXISTS idx_players_username ON players(username);