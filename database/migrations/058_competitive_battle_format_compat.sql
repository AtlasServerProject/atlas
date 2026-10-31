-- Runtime-only correction. Keep existing ratings and match history unchanged.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'ranked_matches'
          AND column_name = 'validation_version'
    ) THEN
        RAISE EXCEPTION 'Competitive battles require ranked_matches.validation_version (migration 055).';
    END IF;
END $$;
