-- Native transient team stores do not add persistent Pokémon or change ratings.
-- Require the existing ranking journal before enabling the corrected battle path.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'ranked_matches' AND column_name = 'battle_id'
    ) THEN
        RAISE EXCEPTION 'Competitive clone ownership requires ranked_matches.battle_id (migration 054).';
    END IF;
END $$;
