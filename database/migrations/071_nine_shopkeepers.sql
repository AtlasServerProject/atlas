-- Catalogue installation is versioned; actual item IDs are read from the installed registry.
CREATE TABLE npc_shop_catalogue_versions (
 version VARCHAR(80) PRIMARY KEY,
 installed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 offer_count INTEGER NOT NULL CHECK(offer_count>0)
);
