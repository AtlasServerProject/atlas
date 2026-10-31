-- Fossil monitor sold in the Cobblemon machines shop; its crafting recipe is removed by Core 1.40.5+machines.1.
INSERT INTO npc_shop_offers(shop_id,item_id,buy_price,sell_price,stock_chance,price_variation,sort_order,enabled)
VALUES ('machines','cobblemon:monitor',100000,0,1,0,1410,true)
ON CONFLICT (shop_id,item_id) DO NOTHING;
