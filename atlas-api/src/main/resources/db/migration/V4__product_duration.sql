ALTER TABLE atlas_web.products ALTER COLUMN duration_days DROP NOT NULL;
ALTER TABLE atlas_web.products DROP CONSTRAINT products_duration_days_check;
UPDATE atlas_web.products SET duration_days=NULL WHERE category<>'VIPs';
ALTER TABLE atlas_web.products ADD CONSTRAINT products_duration_consistency CHECK((category='VIPs' AND duration_days IS NOT NULL AND duration_days=30) OR (category<>'VIPs' AND duration_days IS NULL));
UPDATE atlas_web.system_metadata SET schema_generation=4 WHERE id=1;
