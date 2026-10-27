-- Use Cobblemon's own starter-selected state; never reset or duplicate it in SQL.
ALTER TABLE lobby_npc_destinations ADD COLUMN IF NOT EXISTS action TEXT NOT NULL DEFAULT 'TELEPORT';
INSERT INTO lobby_npc_destinations(npc_tag,label,world,x,y,z,yaw,pitch,action) VALUES
('atlas_npc_emerald_professor_carvalho','Professor Carvalho','atlas:emerald',857.5,78,3750.5,0,0,'STARTER')
ON CONFLICT(npc_tag) DO UPDATE SET label=EXCLUDED.label,world=EXCLUDED.world,
x=EXCLUDED.x,y=EXCLUDED.y,z=EXCLUDED.z,yaw=EXCLUDED.yaw,pitch=EXCLUDED.pitch,action=EXCLUDED.action;
