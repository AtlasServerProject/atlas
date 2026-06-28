CREATE TABLE ranks (
    id BIGSERIAL PRIMARY KEY,
    identifier VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    prefix VARCHAR(30) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    color VARCHAR(20),
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE player_ranks (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    rank_id BIGINT NOT NULL REFERENCES ranks(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(player_id, rank_id)
);

CREATE TABLE rank_permissions (
    id BIGSERIAL PRIMARY KEY,
    rank_id BIGINT NOT NULL REFERENCES ranks(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(rank_id, permission)
);

CREATE INDEX idx_player_ranks_player ON player_ranks(player_id);
CREATE INDEX idx_rank_permissions_rank ON rank_permissions(rank_id);