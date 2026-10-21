ALTER TABLE market_listings ADD COLUMN item_category TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(item_category IN ('UNKNOWN','BLOCKS','MINERALS','POKEBALLS','MODIFIERS','OTHER'));
ALTER TABLE market_listings ADD COLUMN pokemon_flags INTEGER NOT NULL DEFAULT -1 CHECK(pokemon_flags BETWEEN -1 AND 31);
ALTER TABLE market_listings ADD COLUMN server_name TEXT NOT NULL DEFAULT 'Emerald';
ALTER TABLE market_listings ADD COLUMN duration_hours INTEGER NOT NULL DEFAULT 24 CHECK(duration_hours BETWEEN 1 AND 168);
ALTER TABLE market_listings ADD COLUMN expires_at TIMESTAMPTZ;
ALTER TABLE market_listings ADD COLUMN end_reason TEXT CHECK(end_reason IN ('CANCELLED','EXPIRED'));
-- Existing active listings receive a fresh 24-hour window; no assets are removed by this migration.
UPDATE market_listings SET expires_at=now()+interval '24 hours' WHERE state='ACTIVE';
CREATE INDEX market_expiration ON market_listings(expires_at) WHERE state='ACTIVE';
CREATE INDEX market_active_price ON market_listings(price,id) WHERE state='ACTIVE';
