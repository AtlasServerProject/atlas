-- Keep the configured location in sync with the professor's new window-side desk.
-- This is metadata for the STARTER NPC; no player starter data is modified.
UPDATE lobby_npc_destinations
SET x=857.5,y=78,z=3764.5,yaw=180,pitch=0
WHERE npc_tag='atlas_npc_emerald_professor_carvalho' AND action='STARTER';
