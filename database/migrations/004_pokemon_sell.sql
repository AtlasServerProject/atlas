CREATE TABLE pokemon_sell_history (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT REFERENCES players(id),

    species VARCHAR(60),

    level INTEGER,

    shiny BOOLEAN,

    iv_total INTEGER,

    nature VARCHAR(40),

    sold_price NUMERIC(18,2),

    created_at TIMESTAMP DEFAULT NOW()
);