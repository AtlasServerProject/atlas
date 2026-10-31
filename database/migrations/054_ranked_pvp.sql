BEGIN;
CREATE TABLE IF NOT EXISTS ranked_matches (
 id UUID PRIMARY KEY, battle_id UUID UNIQUE,
 tier TEXT NOT NULL CHECK(tier IN ('OU','UU','MONOTYPE','UBERS','AG')),
 first_uuid UUID NOT NULL,first_name TEXT NOT NULL,second_uuid UUID NOT NULL,second_name TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PREPARING','LIVE','SETTLED','VOID')),
 winner_uuid UUID,delta INTEGER,reason TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),settled_at TIMESTAMPTZ,
 CHECK(first_uuid<>second_uuid)
);
CREATE TABLE IF NOT EXISTS ranked_ratings (
 tier TEXT NOT NULL CHECK(tier IN ('OU','UU','MONOTYPE','UBERS','AG')),
 player_uuid UUID NOT NULL,player_name TEXT NOT NULL,
 rating INTEGER NOT NULL DEFAULT 1000 CHECK(rating>=0),wins INTEGER NOT NULL DEFAULT 0 CHECK(wins>=0),losses INTEGER NOT NULL DEFAULT 0 CHECK(losses>=0),
 PRIMARY KEY(tier,player_uuid)
);
CREATE INDEX IF NOT EXISTS ranked_leaderboard ON ranked_ratings(tier,rating DESC,wins DESC,losses,player_uuid);
COMMIT;
