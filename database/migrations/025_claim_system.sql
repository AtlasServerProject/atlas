ALTER TABLE claim_members
    ALTER COLUMN claim_id SET NOT NULL,
    ALTER COLUMN player_id SET NOT NULL,
    ADD COLUMN IF NOT EXISTS trust_level VARCHAR(16) NOT NULL DEFAULT 'ACCESS';

CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_members_unique
ON claim_members(claim_id, player_id);

CREATE INDEX IF NOT EXISTS idx_claim_bounds
ON claims(world, min_x, max_x, min_z, max_z);
