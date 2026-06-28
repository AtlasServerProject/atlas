CREATE TABLE economy_accounts (
    player_id BIGINT PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,

    balance NUMERIC(18,2) NOT NULL DEFAULT 0,

    total_earned NUMERIC(18,2) NOT NULL DEFAULT 0,

    total_spent NUMERIC(18,2) NOT NULL DEFAULT 0,

    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE economy_transactions (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL REFERENCES players(id),

    type VARCHAR(30) NOT NULL,

    amount NUMERIC(18,2) NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_player
ON economy_transactions(player_id);

CREATE INDEX idx_transactions_date
ON economy_transactions(created_at);