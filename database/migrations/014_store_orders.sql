CREATE TABLE store_orders (

    id BIGSERIAL PRIMARY KEY,

    order_uuid UUID NOT NULL UNIQUE,

    player_id BIGINT
        REFERENCES players(id)
        ON DELETE SET NULL,

    buyer_name VARCHAR(32) NOT NULL,

    product_type VARCHAR(30) NOT NULL,

    product_identifier VARCHAR(100) NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 1,

    price NUMERIC(12,2) NOT NULL,

    payment_status VARCHAR(30) NOT NULL,

    delivered BOOLEAN NOT NULL DEFAULT FALSE,

    purchased_at TIMESTAMP DEFAULT NOW(),

    delivered_at TIMESTAMP
);

CREATE INDEX idx_store_player
ON store_orders(player_id);

CREATE INDEX idx_store_status
ON store_orders(payment_status);