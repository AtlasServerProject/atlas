ALTER TABLE atlas_web.users DROP CONSTRAINT users_role_check;
ALTER TABLE atlas_web.users ADD CONSTRAINT users_role_check CHECK(role IN ('USER','SUPPORT','MODERATOR','ADMIN'));
UPDATE atlas_web.system_metadata SET schema_generation=10 WHERE id=1;
