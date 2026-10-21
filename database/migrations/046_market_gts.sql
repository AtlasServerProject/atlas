CREATE TABLE market_listings (
 id UUID PRIMARY KEY,seller UUID NOT NULL,seller_name TEXT NOT NULL,buyer UUID,kind TEXT NOT NULL CHECK(kind IN ('ITEM','POKEMON')),pokemon_uuid UUID,payload JSONB NOT NULL,name TEXT NOT NULL,price BIGINT NOT NULL CHECK(price BETWEEN 1 AND 1000000000),
 state TEXT NOT NULL CHECK(state IN ('PREPARING','ESCROWING','ACTIVE','DEBITING','PAYING','DEBITED','DELIVERING','SOLD','CANCEL_REQUESTED','RETURNING','CANCELLED','VOID','REVIEW')),
 credit_state TEXT NOT NULL DEFAULT 'NONE' CHECK(credit_state IN ('NONE','AVAILABLE','PENDING','PAYING','PAID','REVIEW')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),CHECK(seller IS DISTINCT FROM buyer),CHECK((kind='POKEMON')=(pokemon_uuid IS NOT NULL))
);
CREATE INDEX market_public_list ON market_listings(kind,created_at DESC) WHERE state='ACTIVE';
CREATE INDEX market_owner ON market_listings(seller,kind);
CREATE UNIQUE INDEX market_one_pokemon ON market_listings(pokemon_uuid) WHERE kind='POKEMON' AND state NOT IN ('SOLD','CANCELLED','VOID');
