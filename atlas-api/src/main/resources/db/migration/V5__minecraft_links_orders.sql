CREATE TABLE atlas_web.minecraft_challenges (
 id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES atlas_web.users(id), code_hash CHAR(64) NOT NULL UNIQUE,
 expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('WAITING','PROVED','CONFIRMED','CANCELLED')),
 subject UUID, core_player_id BIGINT, minecraft_uuid UUID, nickname TEXT, server TEXT REFERENCES atlas_web.servers(slug),
 CHECK ((state IN ('WAITING','CANCELLED')) OR (subject IS NOT NULL AND core_player_id>0 AND minecraft_uuid IS NOT NULL AND nickname IS NOT NULL AND server='emerald'))
);
CREATE INDEX minecraft_challenges_user ON atlas_web.minecraft_challenges(user_id,created_at DESC);
CREATE TABLE atlas_web.minecraft_links (
 id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES atlas_web.users(id), subject UUID NOT NULL,
 core_player_id BIGINT NOT NULL CHECK(core_player_id>0), minecraft_uuid UUID NOT NULL, nickname TEXT NOT NULL,
 server TEXT NOT NULL REFERENCES atlas_web.servers(slug) CHECK(server='emerald'), linked_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX minecraft_link_account ON atlas_web.minecraft_links(user_id) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX minecraft_link_player ON atlas_web.minecraft_links(subject) WHERE revoked_at IS NULL;
CREATE TABLE atlas_web.identity_audit (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, user_id UUID NOT NULL REFERENCES atlas_web.users(id),
 action TEXT NOT NULL, subject UUID, request_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
-- Opening sales requires both a deploy-time switch and an explicitly enabled offer.
ALTER TABLE atlas_web.product_servers DROP CONSTRAINT product_servers_purchasable_check;
CREATE TABLE atlas_web.orders (
 id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES atlas_web.users(id), link_id UUID NOT NULL REFERENCES atlas_web.minecraft_links(id),
 product_id BIGINT NOT NULL REFERENCES atlas_web.products(id), idempotency_key VARCHAR(100) NOT NULL, request_hash CHAR(64) NOT NULL,
 snapshot JSONB NOT NULL, total_cents INTEGER NOT NULL CHECK(total_cents>0), currency TEXT NOT NULL CHECK(currency='BRL'),
 quantity INTEGER NOT NULL CHECK(quantity=1), created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
 payment_status TEXT NOT NULL CHECK(payment_status IN ('PENDING','PAID','FAILED','CANCELLED','EXPIRED','REFUNDED','CHARGEBACK')),
 delivery_status TEXT NOT NULL CHECK(delivery_status IN ('WAITING','PROCESSING','DELIVERED','RETRY','REVIEW')),
 UNIQUE(user_id,idempotency_key), CHECK(expires_at>created_at)
);
CREATE INDEX orders_account ON atlas_web.orders(user_id,created_at DESC,id);
CREATE TABLE atlas_web.order_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, order_id UUID NOT NULL REFERENCES atlas_web.orders(id),
 event TEXT NOT NULL, request_id TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL
);
-- Row-level SHARE locks require UPDATE privilege. No public server mutation is exposed.
GRANT UPDATE(active) ON atlas_web.servers TO atlas_api_runtime;
GRANT SELECT,INSERT,UPDATE ON atlas_web.minecraft_challenges,atlas_web.minecraft_links TO atlas_api_runtime;
GRANT SELECT,INSERT ON atlas_web.identity_audit,atlas_web.orders,atlas_web.order_events TO atlas_api_runtime;
GRANT USAGE,SELECT ON SEQUENCE atlas_web.identity_audit_id_seq,atlas_web.order_events_id_seq TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=5 WHERE id=1;
