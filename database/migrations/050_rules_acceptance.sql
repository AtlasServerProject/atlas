CREATE TABLE IF NOT EXISTS player_rules_acceptance (
    uuid UUID NOT NULL REFERENCES players(uuid),
    rules_version INTEGER NOT NULL CHECK (rules_version > 0),
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (uuid, rules_version)
);
