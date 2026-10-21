CREATE TABLE IF NOT EXISTS commercial_vip_legendary_rewards (
 delivery_id UUID PRIMARY KEY REFERENCES commercial_vip_receipts(delivery_id),
 player_id BIGINT NOT NULL REFERENCES players(id), pokemon_uuid UUID NOT NULL UNIQUE,
 state TEXT NOT NULL DEFAULT 'PENDING' CHECK(state IN ('PENDING','READY','DELIVERING','DELIVERED','REVIEW')),
 pokemon_data JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), delivered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS vip_legendary_pending ON commercial_vip_legendary_rewards(state);
GRANT SELECT, INSERT, UPDATE ON commercial_vip_legendary_rewards TO atlas_app;
