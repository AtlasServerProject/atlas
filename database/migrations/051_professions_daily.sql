CREATE TABLE IF NOT EXISTS profession_progress (
 uuid UUID NOT NULL REFERENCES players(uuid), job TEXT NOT NULL CHECK(job IN ('miner','logger','farmer','fisher','trainer')),
 xp BIGINT NOT NULL DEFAULT 0 CHECK(xp>=0), paid_level INTEGER NOT NULL DEFAULT 0 CHECK(paid_level BETWEEN 0 AND 100),
 PRIMARY KEY(uuid,job)
);
CREATE TABLE IF NOT EXISTS profession_activity (
 event_key TEXT PRIMARY KEY, uuid UUID NOT NULL REFERENCES players(uuid), job TEXT NOT NULL,
 activity_date DATE NOT NULL, xp INTEGER NOT NULL CHECK(xp>0)
);
CREATE INDEX IF NOT EXISTS profession_activity_daily ON profession_activity(uuid,job,activity_date);
CREATE TABLE IF NOT EXISTS profession_placed_blocks (world TEXT NOT NULL,pos BIGINT NOT NULL,PRIMARY KEY(world,pos));
CREATE TABLE IF NOT EXISTS daily_progress (uuid UUID PRIMARY KEY REFERENCES players(uuid),last_claim DATE,day INTEGER NOT NULL DEFAULT 0 CHECK(day BETWEEN 0 AND 30));
CREATE TABLE IF NOT EXISTS engagement_rewards (
 id UUID PRIMARY KEY,uuid UUID NOT NULL REFERENCES players(uuid),source TEXT NOT NULL,claim_key TEXT NOT NULL,
 kind TEXT NOT NULL,value TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),
 state TEXT NOT NULL DEFAULT 'PENDING' CHECK(state IN ('PENDING','READY','DELIVERING','DELIVERED','REVIEW')),
 payload JSONB,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),delivered_at TIMESTAMPTZ,
 UNIQUE(uuid,source,claim_key)
);
CREATE INDEX IF NOT EXISTS engagement_rewards_pending ON engagement_rewards(state) WHERE state NOT IN ('DELIVERED','REVIEW');
