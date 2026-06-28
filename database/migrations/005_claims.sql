CREATE TABLE claims (

    id BIGSERIAL PRIMARY KEY,

    owner_id BIGINT NOT NULL
        REFERENCES players(id)
        ON DELETE CASCADE,

    world VARCHAR(50) NOT NULL,

    min_x INTEGER NOT NULL,
    min_z INTEGER NOT NULL,

    max_x INTEGER NOT NULL,
    max_z INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_claim_owner
ON claims(owner_id);

CREATE INDEX idx_claim_world
ON claims(world);