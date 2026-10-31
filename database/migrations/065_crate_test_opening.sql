CREATE TABLE crate_locations (
 crate_id BIGINT PRIMARY KEY REFERENCES crates(id),
 dimension VARCHAR(80) NOT NULL, x INTEGER NOT NULL,y INTEGER NOT NULL,z INTEGER NOT NULL,
 UNIQUE(dimension,x,y,z)
);
CREATE TABLE crate_settings (
 singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
 free_test BOOLEAN NOT NULL DEFAULT FALSE
);
INSERT INTO crate_settings VALUES(TRUE,TRUE);
CREATE TABLE crate_deliveries (
 id UUID PRIMARY KEY, player_uuid UUID NOT NULL, crate_id BIGINT NOT NULL REFERENCES crates(id),
 pokemon_uuid UUID NOT NULL UNIQUE, reward_identifier VARCHAR(100) NOT NULL,
 pokemon_data JSONB NOT NULL,
 state VARCHAR(16) NOT NULL CHECK(state IN ('READY','DELIVERING','DELIVERED','REVIEW')),
 test BOOLEAN NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), delivered_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX crate_delivery_one_pending ON crate_deliveries(player_uuid) WHERE state IN ('READY','DELIVERING','REVIEW');
INSERT INTO crates(identifier,display_name,description,enabled) VALUES('legendary_monthly','Lendários — Rotação mensal','Teste gratuito: todas as espécies confirmadas; seleção mensal ainda não definida.',TRUE);
INSERT INTO crate_rewards(crate_id,reward_type,reward_identifier,amount,chance)
 SELECT c.id,'POKEMON',r.reward_identifier,1,1.000 FROM crates c CROSS JOIN
 (SELECT DISTINCT reward_identifier FROM crate_rewards WHERE reward_type='POKEMON') r WHERE c.identifier='legendary_monthly';
UPDATE crates SET enabled=TRUE WHERE identifier IN ('generation_1','generation_2','generation_3','generation_4','generation_5','generation_6','generation_7','generation_8','generation_9');
-- In free-test mode chance is a relative weight, not a percentage. No commercial prices/keys.
UPDATE crate_rewards SET chance=1.000 WHERE crate_id IN (SELECT id FROM crates WHERE identifier LIKE 'generation_%');
INSERT INTO crate_locations(crate_id,dimension,x,y,z)
SELECT c.id,'atlas:emerald',v.x,v.y,v.z FROM (VALUES
 ('generation_1',1240,85,4021),('generation_2',1246,85,4021),('generation_3',1243,92,4021),
 ('generation_4',1243,98,4022),('generation_5',1243,104,4022),('generation_6',1243,110,4022),
 ('generation_7',1243,115,4022),('generation_8',1242,120,4021),('generation_9',1244,120,4021),
 ('legendary_monthly',1243,85,4021)) v(identifier,x,y,z) JOIN crates c ON c.identifier=v.identifier;
