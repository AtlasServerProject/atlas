-- Virtual balances only; no physical item representation.
-- Existing table is owned by the database operator. Do not change ownership.
-- Debits require quantity>0 and grants accept only positive bounded amounts.
CREATE TABLE crate_key_ledger(
 id UUID PRIMARY KEY,player_uuid UUID NOT NULL,crate_id BIGINT NOT NULL REFERENCES crates(id),
 delta INTEGER NOT NULL CHECK(delta<>0),reason VARCHAR(40) NOT NULL,actor VARCHAR(80) NOT NULL,
 delivery_id UUID UNIQUE REFERENCES crate_deliveries(id),created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
UPDATE crate_settings SET free_test=FALSE WHERE singleton;
