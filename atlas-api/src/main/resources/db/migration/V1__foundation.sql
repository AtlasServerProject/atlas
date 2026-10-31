-- Schema and roles are provisioned before startup; this migration owns no Core tables.
CREATE TABLE atlas_web.system_metadata (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    schema_generation INTEGER NOT NULL CHECK (schema_generation > 0),
    initialized_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO atlas_web.system_metadata (id, schema_generation) VALUES (1, 1);
GRANT SELECT ON atlas_web.system_metadata TO atlas_api_runtime;
-- Runtime cannot perform DDL or change the migration ledger. Future migrations grant
-- only the required DML privileges on their own tables.
