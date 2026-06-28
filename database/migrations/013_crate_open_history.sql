CREATE TABLE crate_open_history (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    crate_id BIGINT NOT NULL
        REFERENCES crates(id)
        ON DELETE CASCADE,

    reward_type VARCHAR(30) NOT NULL,

    reward_identifier VARCHAR(100) NOT NULL,

    amount INTEGER NOT NULL,

    opened_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crate_history_player
ON crate_open_history(player_id);

CREATE INDEX idx_crate_history_date
ON crate_open_history(opened_at);