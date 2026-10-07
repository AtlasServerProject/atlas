CREATE TABLE IF NOT EXISTS staff_notes (
    id BIGSERIAL PRIMARY KEY,
    target_player_id BIGINT NOT NULL REFERENCES players(id),
    author_uuid UUID,
    author_name VARCHAR(32) NOT NULL,
    body VARCHAR(500) NOT NULL CHECK (char_length(btrim(body)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    archived_by_uuid UUID,
    archived_by_name VARCHAR(32),
    archive_reason VARCHAR(500),
    CHECK ((archived_at IS NULL AND archived_by_name IS NULL AND archive_reason IS NULL)
        OR (archived_at IS NOT NULL AND archived_by_name IS NOT NULL
            AND archive_reason IS NOT NULL AND char_length(btrim(archive_reason)) > 0))
);
CREATE INDEX IF NOT EXISTS idx_staff_notes_target_created
    ON staff_notes(target_player_id, created_at DESC, id DESC);
