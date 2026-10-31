ALTER TABLE market_listings ADD COLUMN duration_seconds INTEGER NOT NULL DEFAULT 86400 CHECK(duration_seconds BETWEEN 1 AND 604800);
UPDATE market_listings SET duration_seconds=duration_hours*3600;
-- Existing expiration timestamps are preserved. The hours column remains for rollback compatibility.
