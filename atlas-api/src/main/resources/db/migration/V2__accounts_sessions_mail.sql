CREATE TABLE atlas_web.users (
 id UUID PRIMARY KEY,
 username VARCHAR(32) NOT NULL,
 email VARCHAR(254) NOT NULL UNIQUE CHECK(email = lower(email)),
 password_hash TEXT NOT NULL,
 role VARCHAR(10) NOT NULL DEFAULT 'USER' CHECK(role IN ('USER','ADMIN')),
 email_verified BOOLEAN NOT NULL DEFAULT FALSE,
 auth_version BIGINT NOT NULL DEFAULT 1,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE atlas_web.auth_tokens (
 id UUID PRIMARY KEY,
 user_id UUID NOT NULL REFERENCES atlas_web.users(id) ON DELETE CASCADE,
 token_hash CHAR(64) NOT NULL UNIQUE,
 purpose VARCHAR(16) NOT NULL CHECK(purpose IN ('VERIFY_EMAIL','RESET_PASSWORD')),
 expires_at TIMESTAMPTZ NOT NULL,
 used_at TIMESTAMPTZ
);
CREATE INDEX auth_tokens_user_idx ON atlas_web.auth_tokens(user_id,purpose);
CREATE TABLE atlas_web.auth_rate_limits (
 bucket_key CHAR(64) PRIMARY KEY,
 window_started_at TIMESTAMPTZ NOT NULL,
 attempts INTEGER NOT NULL CHECK(attempts > 0)
);
CREATE TABLE atlas_web.mail_outbox (
 id UUID PRIMARY KEY,
 encrypted_payload TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 lease_until TIMESTAMPTZ,
 delivered_at TIMESTAMPTZ,
 attempts INTEGER NOT NULL DEFAULT 0,
 status VARCHAR(10) NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','SENT','REVIEW'))
);
CREATE INDEX mail_outbox_pending_idx ON atlas_web.mail_outbox(next_attempt_at) WHERE status='PENDING';
CREATE TABLE atlas_web.auth_audit (
 id UUID PRIMARY KEY,
 actor VARCHAR(100) NOT NULL,
 target_user_id UUID NOT NULL REFERENCES atlas_web.users(id),
 action VARCHAR(32) NOT NULL,
 previous_role VARCHAR(10),
 new_role VARCHAR(10),
 reason VARCHAR(500) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Spring Session JDBC PostgreSQL schema, explicitly migrated and scoped to atlas_web.
CREATE TABLE atlas_web.web_sessions (
 PRIMARY_ID CHAR(36) NOT NULL PRIMARY KEY,
 SESSION_ID CHAR(36) NOT NULL UNIQUE,
 CREATION_TIME BIGINT NOT NULL,
 LAST_ACCESS_TIME BIGINT NOT NULL,
 MAX_INACTIVE_INTERVAL INT NOT NULL,
 EXPIRY_TIME BIGINT NOT NULL,
 PRINCIPAL_NAME VARCHAR(100)
);
CREATE INDEX web_sessions_expiry_idx ON atlas_web.web_sessions(EXPIRY_TIME);
CREATE INDEX web_sessions_principal_idx ON atlas_web.web_sessions(PRINCIPAL_NAME);
CREATE TABLE atlas_web.web_sessions_attributes (
 SESSION_PRIMARY_ID CHAR(36) NOT NULL REFERENCES atlas_web.web_sessions(PRIMARY_ID) ON DELETE CASCADE,
 ATTRIBUTE_NAME VARCHAR(200) NOT NULL,
 ATTRIBUTE_BYTES BYTEA NOT NULL,
 PRIMARY KEY(SESSION_PRIMARY_ID, ATTRIBUTE_NAME)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON atlas_web.users, atlas_web.auth_tokens,
 atlas_web.auth_rate_limits, atlas_web.mail_outbox, atlas_web.web_sessions,
 atlas_web.web_sessions_attributes TO atlas_api_runtime;
GRANT SELECT, INSERT ON atlas_web.auth_audit TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation = 2 WHERE id = 1;
