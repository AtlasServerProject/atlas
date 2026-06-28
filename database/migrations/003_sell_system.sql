CREATE TABLE sell_items (

    id SERIAL PRIMARY KEY,

    minecraft_item VARCHAR(100) UNIQUE NOT NULL,

    display_name VARCHAR(100),

    price NUMERIC(18,2) NOT NULL,

    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE sell_history (

    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT REFERENCES players(id),

    minecraft_item VARCHAR(100),

    quantity INTEGER,

    total NUMERIC(18,2),

    created_at TIMESTAMP DEFAULT NOW()
);