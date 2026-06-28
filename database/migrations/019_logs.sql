CREATE TABLE server_logs (
    id BIGSERIAL PRIMARY KEY,
    log_type VARCHAR(40) NOT NULL,
    actor_player_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_server_logs_type ON server_logs(log_type);
CREATE INDEX idx_server_logs_date ON server_logs(created_at);