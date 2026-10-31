ALTER TABLE legendary_events DROP CONSTRAINT IF EXISTS legendary_events_status_check;
ALTER TABLE legendary_events ADD CONSTRAINT legendary_events_status_check CHECK(status IN ('PENDING','ACTIVE','CAPTURED','DEFEATED','DESPAWNED','EXPIRED','FAILED','LOST'));
