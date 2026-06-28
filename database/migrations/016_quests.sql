CREATE TABLE quests (
    id BIGSERIAL PRIMARY KEY,
    identifier VARCHAR(80) UNIQUE NOT NULL,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    quest_type VARCHAR(40) NOT NULL,
    target_identifier VARCHAR(100),
    target_amount INTEGER NOT NULL DEFAULT 1,
    reward_money NUMERIC(12,2) NOT NULL DEFAULT 0,
    reward_data JSONB,
    repeatable BOOLEAN NOT NULL DEFAULT FALSE,
    cooldown_hours INTEGER DEFAULT 24,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE player_quests (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES players(id) ON DELETE CASCADE,
    quest_id BIGINT REFERENCES quests(id) ON DELETE CASCADE,
    progress INTEGER NOT NULL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(player_id, quest_id)
);