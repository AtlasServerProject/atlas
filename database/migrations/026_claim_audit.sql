CREATE TABLE IF NOT EXISTS claim_audit_log (
    id BIGSERIAL PRIMARY KEY,
    claim_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    actor_uuid UUID NOT NULL,
    actor_name VARCHAR(16) NOT NULL,
    action VARCHAR(32) NOT NULL,
    world VARCHAR(128) NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    z INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claim_audit_claim_created
ON claim_audit_log(claim_id, created_at DESC);
