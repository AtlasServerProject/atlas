ALTER TABLE atlas_web.users ADD COLUMN mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE atlas_web.account_mfa (
 user_id UUID PRIMARY KEY REFERENCES atlas_web.users(id) ON DELETE CASCADE,
 secret_ciphertext TEXT,
 pending_ciphertext TEXT,
 pending_expires_at TIMESTAMPTZ,
 enabled_at TIMESTAMPTZ,
 last_step BIGINT NOT NULL DEFAULT -1
);
CREATE TABLE atlas_web.mfa_recovery_codes (
 user_id UUID NOT NULL REFERENCES atlas_web.users(id) ON DELETE CASCADE,
 code_hash CHAR(64) NOT NULL,
 PRIMARY KEY(user_id,code_hash)
);
CREATE TABLE atlas_web.security_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 user_id UUID,
 action VARCHAR(40) NOT NULL,
 result VARCHAR(16) NOT NULL,
 request_id VARCHAR(100) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX security_events_time_idx ON atlas_web.security_events(created_at);
GRANT SELECT,INSERT,UPDATE,DELETE ON atlas_web.account_mfa,atlas_web.mfa_recovery_codes TO atlas_api_runtime;
GRANT INSERT,SELECT ON atlas_web.security_events TO atlas_api_runtime;
GRANT USAGE,SELECT ON SEQUENCE atlas_web.security_events_id_seq TO atlas_api_runtime;
-- Runtime cannot change roles. Role administration remains an explicit operator/migration action.
REVOKE INSERT ON atlas_web.users FROM atlas_api_runtime;
GRANT INSERT(id,username,email,password_hash,created_at) ON atlas_web.users TO atlas_api_runtime;
REVOKE UPDATE ON atlas_web.users FROM atlas_api_runtime;
GRANT UPDATE(username,email,password_hash,email_verified,auth_version,mfa_enabled) ON atlas_web.users TO atlas_api_runtime;
-- Deliberately bounded cleanup, no business/order/ticket data or dynamic SQL.
CREATE FUNCTION atlas_web.prune_security_ephemera() RETURNS void
LANGUAGE SQL SECURITY DEFINER SET search_path = pg_catalog,atlas_web AS $$
 DELETE FROM atlas_web.auth_tokens WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
 DELETE FROM atlas_web.auth_rate_limits WHERE window_started_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
 DELETE FROM atlas_web.account_mfa WHERE enabled_at IS NULL AND pending_expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';
$$;
REVOKE ALL ON FUNCTION atlas_web.prune_security_ephemera() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION atlas_web.prune_security_ephemera() TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=12 WHERE id=1;
