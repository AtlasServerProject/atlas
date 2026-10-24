BEGIN;
CREATE TABLE IF NOT EXISTS atlas_tournaments (
 id UUID PRIMARY KEY,
 slug TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL,
 format TEXT NOT NULL DEFAULT 'atlasgen9ou' CHECK(format='atlasgen9ou'),
 capacity INTEGER NOT NULL DEFAULT 16 CHECK(capacity=16),
 state TEXT NOT NULL CHECK(state IN ('CREATING','OPEN','FULL','STARTED','CANCELLED','COMPLETE','REVIEW')),
 created_by TEXT NOT NULL,
 remote_id TEXT,
 revision INTEGER NOT NULL DEFAULT 0,
 synced_revision INTEGER NOT NULL DEFAULT -1,
 last_error TEXT,
 retry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS atlas_one_live_tournament ON atlas_tournaments((true)) WHERE state NOT IN ('CANCELLED','COMPLETE');
CREATE TABLE IF NOT EXISTS atlas_tournament_entries (
 tournament_id UUID NOT NULL REFERENCES atlas_tournaments(id),
 player_uuid UUID NOT NULL,
 player_name TEXT NOT NULL,
 active BOOLEAN NOT NULL DEFAULT true,
 joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tournament_id,player_uuid)
);
CREATE TABLE IF NOT EXISTS atlas_tournament_announcements (
 id BIGSERIAL PRIMARY KEY,
 tournament_id UUID NOT NULL REFERENCES atlas_tournaments(id),
 message TEXT NOT NULL,
 delivered BOOLEAN NOT NULL DEFAULT false,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMIT;
