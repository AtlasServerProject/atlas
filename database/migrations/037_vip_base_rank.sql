-- Fresh databases had only VIP 2/3: migration 030 updated a VIP 1 row
-- that was absent. Commercial VIP 1 needs this definition to resolve
-- its effective rank, permissions and display; no player rank is assigned.
INSERT INTO ranks (identifier, display_name, prefix, priority, color, is_staff, enabled)
VALUES ('vip', 'VIP', '[VIP]', 20, 'gold', false, true)
ON CONFLICT (identifier) DO NOTHING;
