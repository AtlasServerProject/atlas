ALTER TABLE atlas_web.delivery_outbox ADD COLUMN lease_token UUID, ADD COLUMN lease_until TIMESTAMPTZ, ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0), ADD COLUMN next_attempt TIMESTAMPTZ NOT NULL DEFAULT now(), ADD COLUMN last_error TEXT, ADD COLUMN receipt JSONB, ADD COLUMN ack_token UUID;
CREATE INDEX delivery_due ON atlas_web.delivery_outbox(next_attempt) WHERE state='WAITING';
CREATE TABLE atlas_web.vip_mirrors(subject UUID PRIMARY KEY,core_player_id BIGINT NOT NULL CHECK(core_player_id>0),server TEXT NOT NULL CHECK(server='emerald'),vip1_ms BIGINT NOT NULL CHECK(vip1_ms>=0),vip2_ms BIGINT NOT NULL CHECK(vip2_ms>=0),vip3_ms BIGINT NOT NULL CHECK(vip3_ms>=0),checkpoint TIMESTAMPTZ NOT NULL,updated_at TIMESTAMPTZ NOT NULL);
CREATE TABLE atlas_web.delivery_audit(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,delivery_id UUID NOT NULL REFERENCES atlas_web.delivery_outbox(id),actor UUID REFERENCES atlas_web.users(id),action TEXT NOT NULL,reason TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL);
GRANT SELECT,INSERT,UPDATE ON atlas_web.vip_mirrors TO atlas_api_runtime;
GRANT SELECT,INSERT ON atlas_web.delivery_audit TO atlas_api_runtime;
GRANT USAGE,SELECT ON SEQUENCE atlas_web.delivery_audit_id_seq TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=8 WHERE id=1;
