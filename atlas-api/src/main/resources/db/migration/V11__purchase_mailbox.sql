ALTER TABLE atlas_web.delivery_outbox ADD COLUMN activation_requested_at TIMESTAMPTZ;
-- Preserve deliveries already applied before this change; unactivated purchases wait indefinitely.
UPDATE atlas_web.delivery_outbox SET activation_requested_at=created_at WHERE state='DELIVERED' OR receipt IS NOT NULL;
CREATE INDEX mailbox_activation_due ON atlas_web.delivery_outbox(next_attempt) WHERE state='WAITING' AND activation_requested_at IS NOT NULL;
UPDATE atlas_web.system_metadata SET schema_generation=11 WHERE id=1;
