CREATE TABLE atlas_web.payment_attempts (
 id UUID PRIMARY KEY, order_id UUID NOT NULL UNIQUE REFERENCES atlas_web.orders(id),
 mode TEXT NOT NULL CHECK(mode IN ('test','production')), state TEXT NOT NULL CHECK(state IN ('CREATING','READY','UNKNOWN','REVIEW')),
 preference_id TEXT UNIQUE, checkout_url TEXT, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL,
 CHECK((state='READY') = (preference_id IS NOT NULL AND checkout_url IS NOT NULL))
);
CREATE TABLE atlas_web.payment_jobs (
 payment_id VARCHAR(30) PRIMARY KEY CHECK(payment_id ~ '^[0-9]+$'), generation BIGINT NOT NULL DEFAULT 1,
 completed_generation BIGINT NOT NULL DEFAULT 0, next_attempt TIMESTAMPTZ NOT NULL DEFAULT now(),
 lease_until TIMESTAMPTZ, lease_token UUID, failures INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE atlas_web.payment_observations (
 payment_id VARCHAR(30) PRIMARY KEY, order_id UUID NOT NULL REFERENCES atlas_web.orders(id),
 provider_status TEXT NOT NULL, changed_at TIMESTAMPTZ NOT NULL, checked_at TIMESTAMPTZ NOT NULL,
 UNIQUE(order_id,payment_id)
);
CREATE TABLE atlas_web.payment_webhooks (
 event_hash CHAR(64) PRIMARY KEY, payment_id VARCHAR(30) NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE atlas_web.delivery_outbox (
 id UUID PRIMARY KEY, order_id UUID NOT NULL UNIQUE REFERENCES atlas_web.orders(id),
 state TEXT NOT NULL DEFAULT 'WAITING' CHECK(state IN ('WAITING','REVIEW','DELIVERED')),
 created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE atlas_web.payment_reviews (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, payment_id VARCHAR(30) NOT NULL,
 reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(payment_id,reason)
);
GRANT SELECT,INSERT,UPDATE ON atlas_web.payment_attempts,atlas_web.payment_jobs,atlas_web.payment_observations,atlas_web.delivery_outbox TO atlas_api_runtime;
GRANT SELECT,INSERT ON atlas_web.payment_webhooks,atlas_web.payment_reviews TO atlas_api_runtime;
GRANT USAGE,SELECT ON SEQUENCE atlas_web.payment_reviews_id_seq TO atlas_api_runtime;
GRANT UPDATE(payment_status,delivery_status) ON atlas_web.orders TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=7 WHERE id=1;
