-- Public Emerald navigation destinations, independent of NPC appearance/position.
CREATE TABLE IF NOT EXISTS lobby_npc_destinations (
    npc_tag TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    world TEXT NOT NULL,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    yaw REAL NOT NULL DEFAULT 0,
    pitch REAL NOT NULL DEFAULT 0
);
INSERT INTO lobby_npc_destinations(npc_tag,label,world,x,y,z,yaw,pitch) VALUES
('atlas_npc_emerald_arena','Arena','atlas:emerald',848.5,59,3655.5,90,0),
('atlas_npc_emerald_mercado','Mercado','atlas:emerald',957.5,75,3763.5,180,0),
('atlas_npc_emerald_tutorial','Tutorial','atlas:emerald',857.5,72,3776.5,180,0),
('atlas_npc_emerald_caixas','Caixas','atlas:emerald',924.5,55,3866.5,-90,0)
ON CONFLICT (npc_tag) DO UPDATE SET label=EXCLUDED.label,world=EXCLUDED.world,
x=EXCLUDED.x,y=EXCLUDED.y,z=EXCLUDED.z,yaw=EXCLUDED.yaw,pitch=EXCLUDED.pitch;
