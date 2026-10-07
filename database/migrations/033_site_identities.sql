-- Stable site subject follows players.id through a Premium promotion.
CREATE TABLE IF NOT EXISTS site_identities (
 subject UUID PRIMARY KEY,
 player_id BIGINT NOT NULL UNIQUE REFERENCES players(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
GRANT SELECT,INSERT,UPDATE ON site_identities TO atlas_app;
