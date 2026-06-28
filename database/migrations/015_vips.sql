CREATE TABLE vip_plans (
    id BIGSERIAL PRIMARY KEY,

    identifier VARCHAR(50) UNIQUE NOT NULL,

    display_name VARCHAR(100) NOT NULL,

    description TEXT,

    duration_days INTEGER NOT NULL DEFAULT 30,

    price NUMERIC(12,2) NOT NULL,

    benefits JSONB NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE player_vips (
    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    vip_plan_id BIGINT NOT NULL
        REFERENCES vip_plans(id)
        ON DELETE CASCADE,

    starts_at TIMESTAMP NOT NULL DEFAULT NOW(),

    expires_at TIMESTAMP NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    source VARCHAR(30) NOT NULL DEFAULT 'STORE',

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_player_vips_player
ON player_vips(player_id);

CREATE INDEX idx_player_vips_active
ON player_vips(active);

CREATE INDEX idx_player_vips_expires
ON player_vips(expires_at);