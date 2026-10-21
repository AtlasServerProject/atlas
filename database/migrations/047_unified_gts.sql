-- Unified GTS quotas count items and Pokemon together; existing listings are preserved.
CREATE INDEX market_active_owner ON market_listings(seller) WHERE state NOT IN ('SOLD','CANCELLED','VOID');
