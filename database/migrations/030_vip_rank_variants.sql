INSERT INTO ranks (identifier, display_name, prefix, priority, color, is_staff, enabled)
VALUES
    ('vipplus', 'VIP ✦', '[VIP ✦]', 30, 'aqua', false, true),
    ('vipplusplus', 'VIP ✦✦', '[VIP ✦✦]', 40, 'light_purple', false, true)
ON CONFLICT (identifier)
DO UPDATE SET
    display_name = EXCLUDED.display_name,
    prefix = EXCLUDED.prefix,
    priority = EXCLUDED.priority,
    color = EXCLUDED.color,
    is_staff = EXCLUDED.is_staff,
    enabled = true;

UPDATE ranks
SET display_name = 'VIP',
    prefix = '[VIP]',
    priority = 20,
    color = 'gold',
    is_staff = false,
    enabled = true
WHERE LOWER(identifier) = 'vip';
