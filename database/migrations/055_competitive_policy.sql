BEGIN;
ALTER TABLE ranked_matches ADD COLUMN IF NOT EXISTS validation_version TEXT NOT NULL DEFAULT 'legacy-unvalidated';
COMMIT;
