CREATE TABLE atlas_web.external_identities (
 provider VARCHAR(20) NOT NULL CHECK(provider='GOOGLE'),
 subject VARCHAR(255) NOT NULL,
 user_id UUID NOT NULL REFERENCES atlas_web.users(id) ON DELETE CASCADE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(provider,subject),
 UNIQUE(provider,user_id)
);
GRANT SELECT,INSERT ON atlas_web.external_identities TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=13 WHERE id=1;
CREATE TABLE atlas_web.google_login_challenges (
 nonce_hash CHAR(64) PRIMARY KEY,
 expires_at TIMESTAMPTZ NOT NULL
);
GRANT SELECT,INSERT,DELETE ON atlas_web.google_login_challenges TO atlas_api_runtime;
CREATE OR REPLACE FUNCTION atlas_web.prune_security_ephemera() RETURNS void
LANGUAGE SQL SECURITY DEFINER SET search_path = pg_catalog,atlas_web AS $$
 DELETE FROM atlas_web.auth_tokens WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
 DELETE FROM atlas_web.auth_rate_limits WHERE window_started_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.account_mfa WHERE enabled_at IS NULL AND pending_expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.google_login_challenges WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
$$;
