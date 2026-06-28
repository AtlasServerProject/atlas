CREATE TABLE homes (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT
        REFERENCES players(id)
        ON DELETE CASCADE,

    name VARCHAR(32),

    world VARCHAR(50),

    x DOUBLE PRECISION,

    y DOUBLE PRECISION,

    z DOUBLE PRECISION,

    yaw REAL,

    pitch REAL
);