BEGIN;
ALTER TABLE atlas_tournaments DROP CONSTRAINT IF EXISTS atlas_tournaments_capacity_check;
ALTER TABLE atlas_tournaments ADD CONSTRAINT atlas_tournaments_capacity_check CHECK(capacity IN (8,16));
ALTER TABLE atlas_tournaments DROP CONSTRAINT IF EXISTS atlas_tournaments_format_check;
ALTER TABLE atlas_tournaments ADD CONSTRAINT atlas_tournaments_format_check CHECK(format IN ('atlasgen9ou','atlasgen9uu','atlasgen9monotype','atlasgen9ubers','atlasgen9ag'));
ALTER TABLE atlas_tournaments ADD COLUMN IF NOT EXISTS registration_deadline TIMESTAMPTZ NOT NULL DEFAULT (now()+interval '30 minutes');
COMMIT;
