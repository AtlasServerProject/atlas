CREATE TABLE IF NOT EXISTS pokedex_progress (
 uuid UUID PRIMARY KEY, username TEXT NOT NULL,
 milestone INTEGER NOT NULL CHECK(milestone BETWEEN 0 AND 100 AND milestone%10=0),
 caught INTEGER NOT NULL CHECK(caught>=0),total INTEGER NOT NULL CHECK(total>0),
 completed_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pokedex_professors ON pokedex_progress(completed_at) WHERE completed_at IS NOT NULL;
