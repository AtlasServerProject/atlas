-- Temporary bans reuse BAN + expires_at; no schema or historical data rewrite is needed.
-- Validate compatibility before installing the command, without requiring table ownership.
DO $$
BEGIN
    IF (SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'moderation_punishments'
          AND column_name IN ('expires_at', 'revoked_at')
          AND data_type = 'timestamp without time zone') <> 2 THEN
        RAISE EXCEPTION 'Temporary bans require the moderation expiration/revocation schema (migration 028)';
    END IF;
END $$;
