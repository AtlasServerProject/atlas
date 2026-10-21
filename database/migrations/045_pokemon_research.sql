CREATE TABLE research_captures (
 pokemon_uuid UUID PRIMARY KEY,uuid UUID NOT NULL,species TEXT NOT NULL,types TEXT[] NOT NULL CHECK(cardinality(types) BETWEEN 1 AND 2),captured_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX research_captures_player ON research_captures(uuid);
CREATE TABLE research_payments (
 id UUID PRIMARY KEY,uuid UUID NOT NULL,track TEXT NOT NULL CHECK(track IN ('captures','species','types')),stage INTEGER NOT NULL CHECK(stage BETWEEN 1 AND 5),amount BIGINT NOT NULL CHECK(amount BETWEEN 250 AND 10000),
 state TEXT NOT NULL CHECK(state IN ('PENDING','PAYING','PAID','REVIEW')),created_at TIMESTAMPTZ NOT NULL DEFAULT now(),paid_at TIMESTAMPTZ,UNIQUE(uuid,track,stage)
);
CREATE INDEX research_payments_pending ON research_payments(created_at) WHERE state IN ('PENDING','PAYING');
