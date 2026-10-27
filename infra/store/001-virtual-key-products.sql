-- Data-only migration. Reuse existing audited API operations; no new privileges.
-- Idempotence is recorded in the existing catalogue audit ledger.
DO $migration$
DECLARE item RECORD; seed_product_id BIGINT;
BEGIN
 PERFORM pg_advisory_xact_lock(26102026,10);
 IF EXISTS(SELECT 1 FROM atlas_web.catalog_audit WHERE action='DATA_MIGRATION' AND resource='migration:virtual-key-products-v1') THEN RETURN; END IF;
 FOR item IN SELECT * FROM (VALUES
('key-generation-1','Chave 1ª geração — Kanto','Uma chave virtual para abrir a caixa da 1ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',899),
('key-generation-2','Chave 2ª geração — Johto','Uma chave virtual para abrir a caixa da 2ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1399),
('key-generation-3','Chave 3ª geração — Hoenn','Uma chave virtual para abrir a caixa da 3ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1599),
('key-generation-4','Chave 4ª geração — Sinnoh','Uma chave virtual para abrir a caixa da 4ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1899),
('key-generation-5','Chave 5ª geração — Unova','Uma chave virtual para abrir a caixa da 5ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1699),
('key-generation-6','Chave 6ª geração — Kalos','Uma chave virtual para abrir a caixa da 6ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1799),
('key-generation-7','Chave 7ª geração — Alola','Uma chave virtual para abrir a caixa da 7ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',1599),
('key-generation-8','Chave 8ª geração — Galar','Uma chave virtual para abrir a caixa da 8ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',2099),
('key-generation-9','Chave 9ª geração — Paldea','Uma chave virtual para abrir a caixa da 9ª geração. Consulte seu saldo em /compras e use na caixa correspondente.',2599),
('key-legendary-monthly','Chave Lendários do mês','Uma chave virtual para a caixa mensal com dez lendários da seleção vigente. Consulte o saldo em /compras.',1899)) AS seed(slug,name,description,price_cents) LOOP
  IF EXISTS(SELECT 1 FROM atlas_web.products WHERE slug=item.slug AND category<>'Chaves') THEN RAISE EXCEPTION 'Key slug already used by another category'; END IF;
  INSERT INTO atlas_web.products(slug,name,description,category,active,duration_days)
  VALUES(item.slug,item.name,item.description,'Chaves',TRUE,NULL) ON CONFLICT(slug) DO NOTHING;
  SELECT id INTO STRICT seed_product_id FROM atlas_web.products WHERE slug=item.slug;
  INSERT INTO atlas_web.product_servers(product_id,server,price_cents,active,purchasable)
  VALUES(seed_product_id,'emerald',item.price_cents,TRUE,FALSE) ON CONFLICT DO NOTHING;
  INSERT INTO atlas_web.product_versions(product_id,revision,snapshot)
  SELECT p.id,p.revision,to_jsonb(p)||jsonb_build_object('priceCents',s.price_cents,'server',s.server)
  FROM atlas_web.products p JOIN atlas_web.product_servers s ON s.product_id=p.id
  WHERE p.id=seed_product_id AND s.server='emerald' ON CONFLICT DO NOTHING;
 END LOOP;
 INSERT INTO atlas_web.catalog_audit(actor,action,resource,before_data,after_data,request_id)
 SELECT NULL,'DATA_MIGRATION','migration:virtual-key-products-v1',NULL,
 jsonb_agg(jsonb_build_object('id',p.id,'slug',p.slug,'priceCents',s.price_cents,'purchasable',s.purchasable)),
 'virtual-key-products-v1'
 FROM atlas_web.products p JOIN atlas_web.product_servers s ON s.product_id=p.id AND s.server='emerald'
 WHERE p.slug IN ('key-generation-1','key-generation-2','key-generation-3','key-generation-4','key-generation-5','key-generation-6','key-generation-7','key-generation-8','key-generation-9','key-legendary-monthly');
 UPDATE atlas_web.catalog_state SET revision=revision+1 WHERE id=1;
END $migration$;
