CREATE TABLE rtp_logs (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES players(id) ON DELETE CASCADE,
    world VARCHAR(50) NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    z INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rtp_player ON rtp_logs(player_id);
CREATE INDEX idx_rtp_date ON rtp_logs(created_at);