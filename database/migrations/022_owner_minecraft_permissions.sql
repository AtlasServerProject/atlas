UPDATE ranks
SET display_name = 'Dono',
    prefix = '[DONO]'
WHERE LOWER(identifier) = 'owner';

INSERT INTO rank_permissions (rank_id, permission, enabled)
SELECT id, 'minecraft.*', true
FROM ranks
WHERE LOWER(identifier) = 'owner'
ON CONFLICT (rank_id, permission)
DO UPDATE SET enabled = true;
