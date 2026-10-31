-- Existing rank permission model; no schema or ownership changes.
INSERT INTO rank_permissions (rank_id, permission, enabled)
SELECT id, 'worldedit.*', true FROM ranks
WHERE upper(identifier) IN ('ADM', 'ADMIN', 'DONO', 'OWNER')
ON CONFLICT (rank_id, permission) DO UPDATE SET enabled = true;
