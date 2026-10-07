CREATE TABLE IF NOT EXISTS commercial_vip_balances (
 player_id BIGINT NOT NULL REFERENCES players(id),subject UUID NOT NULL REFERENCES site_identities(subject),server TEXT NOT NULL CHECK(server='emerald'),vip1_ms BIGINT NOT NULL DEFAULT 0 CHECK(vip1_ms BETWEEN 0 AND 3153600000000),vip2_ms BIGINT NOT NULL DEFAULT 0 CHECK(vip2_ms BETWEEN 0 AND 3153600000000),vip3_ms BIGINT NOT NULL DEFAULT 0 CHECK(vip3_ms BETWEEN 0 AND 3153600000000),checkpoint TIMESTAMPTZ NOT NULL,PRIMARY KEY(player_id,server),UNIQUE(subject,server)
);
CREATE TABLE IF NOT EXISTS commercial_vip_receipts (
 delivery_id UUID PRIMARY KEY,receipt_id UUID NOT NULL UNIQUE,player_id BIGINT NOT NULL REFERENCES players(id),subject UUID NOT NULL REFERENCES site_identities(subject),server TEXT NOT NULL CHECK(server='emerald'),mode TEXT NOT NULL CHECK(mode IN('production','test')),plan TEXT NOT NULL CHECK(plan IN('vip-1','vip-2','vip-3')),days INTEGER NOT NULL CHECK(days=30),activated_at TIMESTAMPTZ NOT NULL,fingerprint CHAR(64) NOT NULL
);
GRANT SELECT,INSERT,UPDATE ON commercial_vip_balances TO atlas_app;
GRANT SELECT,INSERT ON commercial_vip_receipts TO atlas_app;
