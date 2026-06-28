CREATE TABLE player_keys (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    crate_id BIGINT NOT NULL
        REFERENCES crates(id)
        ON DELETE CASCADE,

    quantity INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(player_id, crate_id)
);