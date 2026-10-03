CREATE TABLE IF NOT EXISTS daily_kit_claims (
    player_uuid UUID NOT NULL,
    kit_id VARCHAR(32) NOT NULL,
    claimed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_uuid, kit_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_kit_claims_claimed_at
ON daily_kit_claims(claimed_at);
