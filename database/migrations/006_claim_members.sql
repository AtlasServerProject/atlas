CREATE TABLE claim_members (

    id BIGSERIAL PRIMARY KEY,

    claim_id BIGINT
        REFERENCES claims(id)
        ON DELETE CASCADE,

    player_id BIGINT
        REFERENCES players(id)
        ON DELETE CASCADE,

    can_build BOOLEAN DEFAULT FALSE,

    can_break BOOLEAN DEFAULT FALSE,

    can_open BOOLEAN DEFAULT FALSE,

    can_interact BOOLEAN DEFAULT FALSE
);