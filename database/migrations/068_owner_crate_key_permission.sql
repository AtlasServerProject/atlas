-- Explicit least-privilege grant for the Dono virtual-key test command.
INSERT INTO rank_permissions(rank_id,permission,enabled)
SELECT id,'atlas.crates.keys.grant',TRUE FROM ranks WHERE lower(identifier)='owner'
ON CONFLICT(rank_id,permission) DO UPDATE SET enabled=TRUE;
