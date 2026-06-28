CREATE TABLE auth_accounts (
    id BIGSERIAL PRIMARY KEY,

    player_id BIGINT NOT NULL UNIQUE
        REFERENCES players(id)
        ON DELETE CASCADE,

    email VARCHAR(120) UNIQUE,

    password_hash TEXT NOT NULL,

    last_ip VARCHAR(60),

    is_premium BOOLEAN NOT NULL DEFAULT FALSE,

    is_verified BOOLEAN NOT NULL DEFAULT FALSE,

    registered_at TIMESTAMP NOT NULL DEFAULT NOW(),

    last_login TIMESTAMP
);

CREATE INDEX idx_auth_email ON auth_accounts(email);
CREATE INDEX idx_auth_player ON auth_accounts(player_id);