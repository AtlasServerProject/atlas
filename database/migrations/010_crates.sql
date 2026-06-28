CREATE TABLE crates (

    id BIGSERIAL PRIMARY KEY,

    identifier VARCHAR(50) UNIQUE NOT NULL,

    display_name VARCHAR(100) NOT NULL,

    description TEXT,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE crate_rewards (

    id BIGSERIAL PRIMARY KEY,

    crate_id BIGINT NOT NULL
        REFERENCES crates(id)
        ON DELETE CASCADE,

    reward_type VARCHAR(30) NOT NULL,

    reward_identifier VARCHAR(100) NOT NULL,

    amount INTEGER NOT NULL DEFAULT 1,

    chance DECIMAL(6,3) NOT NULL
);

CREATE INDEX idx_rewards_crate
ON crate_rewards(crate_id);