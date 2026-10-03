-- Retire pending legacy 43-character challenges; confirmed links are untouched.
UPDATE atlas_web.minecraft_challenges SET state='CANCELLED' WHERE state IN ('WAITING','PROVED');
ALTER TABLE atlas_web.minecraft_challenges DROP CONSTRAINT minecraft_challenges_code_hash_key;
CREATE UNIQUE INDEX minecraft_code_live ON atlas_web.minecraft_challenges(code_hash) WHERE state IN ('WAITING','PROVED');
CREATE INDEX minecraft_code_history ON atlas_web.minecraft_challenges(code_hash,created_at DESC);
CREATE INDEX minecraft_code_expiry ON atlas_web.minecraft_challenges(expires_at) WHERE state IN ('WAITING','PROVED');
UPDATE atlas_web.system_metadata SET schema_generation=6 WHERE id=1;
