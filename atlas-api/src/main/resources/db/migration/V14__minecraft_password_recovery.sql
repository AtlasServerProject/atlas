CREATE TABLE atlas_web.minecraft_password_recovery (
 minecraft_uuid UUID PRIMARY KEY,
 link_id UUID NOT NULL REFERENCES atlas_web.minecraft_links(id),
 code_hash CHAR(64) NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
 consumed BOOLEAN NOT NULL DEFAULT FALSE
);
GRANT SELECT,INSERT,UPDATE,DELETE ON atlas_web.minecraft_password_recovery TO atlas_api_runtime;
CREATE OR REPLACE FUNCTION atlas_web.prune_security_ephemera() RETURNS void
LANGUAGE SQL SECURITY DEFINER SET search_path = pg_catalog,atlas_web AS $$
 DELETE FROM atlas_web.auth_tokens WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
 DELETE FROM atlas_web.auth_rate_limits WHERE window_started_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.account_mfa WHERE enabled_at IS NULL AND pending_expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.google_login_challenges WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.minecraft_password_recovery WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
$$;
UPDATE atlas_web.system_metadata SET schema_generation=14 WHERE id=1;
CREATE TABLE atlas_web.minecraft_recovery_email (
 minecraft_uuid UUID PRIMARY KEY,
 email VARCHAR(254),
 pending_email VARCHAR(254),
 code_hash CHAR(64),
 expires_at TIMESTAMPTZ,
 attempts INTEGER NOT NULL DEFAULT 0,
 verified_at TIMESTAMPTZ
);
GRANT SELECT,INSERT,UPDATE ON atlas_web.minecraft_recovery_email TO atlas_api_runtime;
ALTER TABLE atlas_web.minecraft_password_recovery ALTER COLUMN link_id DROP NOT NULL;
ALTER TABLE atlas_web.minecraft_password_recovery ADD COLUMN recovery_email VARCHAR(254);
