CREATE TABLE gts_listings (
    id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT REFERENCES players(id) ON DELETE CASCADE,
    buyer_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    pokemon_data JSONB NOT NULL,
    price NUMERIC(18,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    sold_at TIMESTAMP
);

CREATE INDEX idx_gts_status ON gts_listings(status);
CREATE INDEX idx_gts_seller ON gts_listings(seller_id);
CREATE INDEX idx_gts_price ON gts_listings(price);