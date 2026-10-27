# Lojistas Atlas

Referência verificada em 26/10/2026: [Pixelmon oficial](https://reforged.gg/en), versão mais recente 9.4.2 beta; recomendada 9.4.1. JAR original baixado do CDN oficial via Modrinth, SHA-1 conferido com a API de distribuição (pixelmon-reference.json). Binário e subsistema NPC/shop extraído ficam em `/home/somente/.cache/atlas-pixelmon-study/`; não foram instalados no Fabric.

Foram examinados os 158 presets de shopkeepers presentes no arquivo, os contratos ShopItem/OpenShopInteractionResult/ShopBuilder e o bytecode de ShopTransactionPacket, ShopItem e OpenShopInteractionResult. Isso cobre catálogo, diálogo/abertura, seleção da oferta, quantidades, compra, venda, verificação da conta e eventos. Não representa leitura de todo o mod ou teste executado dentro do Pixelmon. A wiki [Shopkeeper](https://pixelmonmod.com/wiki/Shopkeeper) descreve especialidades, compra/revenda e variação de estoque/preço; [NPC JSONs](https://pixelmonmod.com/wiki/NPC_JSONs) avisa que parte do conteúdo é antiga. Os presets atuais usam interações e preços por oferta, em vez de depender apenas do antigo shopItems.json.

Implementação Atlas escrita separadamente; não incorpora classes, interfaces gráficas, modelos, texturas ou dependência Pixelmon. Mantém EasyNPC para os personagens, menus de inventário vanilla para compatibilidade e CobbleDollars como moeda.

## Atendimento

| Piso / personagem | Especialidade | Tag existente |
|---|---|---|
| Térreo / Red | Poké Bolas | atlas_npc_pokemart_ground_vendor_1 |
| Térreo / Leaf | Medicamentos | atlas_npc_pokemart_ground_vendor_2 |
| Térreo / Blue | Frutas | atlas_npc_pokemart_ground_vendor_3 |
| Intermediário / Brendan | Evolução | atlas_npc_pokemart_middle_vendor_1 |
| Intermediário / May | Itens de batalha | atlas_npc_pokemart_middle_vendor_2 |
| Superior / Dawn | Vitaminas | atlas_npc_pokemart_vendor_1 |
| Superior / Serena | Mints | atlas_npc_pokemart_vendor_2 |

Botão direito no NPC abre o catálogo. No item, esquerdo seleciona compra e direito seleciona venda. Ajuste 1–64 unidades e confirme; nenhuma ação financeira ocorre ao abrir ou selecionar o item. A venda aceita somente a mesma identificação e componentes do item original: itens renomeados/modificados não são retirados. Inventário cheio impede compra antes do débito; a loja não joga a entrega no chão. Negociação exige login, modo Survival, ausência de batalha, mesma dimensão Emerald e distância máxima de oito blocos até o NPC. Skins, construções e teletransportes não são alterados.

78 ofertas iniciais para os itens correspondentes do Cobblemon instalado. Preços em moeda do jogo, provisórios para balanceamento, definidos explicitamente na migration 070. Nenhuma relação com preços em reais das chaves/site. Venda inicial paga 25% da compra. Objetos do site, chaves, Pokémon e equipamentos modificados não fazem parte do catálogo.

## Configuração e operação

Tabela `npc_shop_offers`: shop_id, item_id, buy_price, sell_price, stock_chance (0–1, sem zero), price_variation (0–10%), sort_order, enabled. Configuração inicial tem chance 1 e variação 0: estoque fixo e preço estável. O suporte a variação diária é determinístico por dia Minecraft do overworld, loja e item; reiniciar não reembaralha o mesmo dia. O preço de compra permanece estritamente acima do de venda. Uma cotação antiga é revalidada antes de qualquer mutação. Evitar cadastrar o mesmo item em lojas com preços de compra inferiores ao de venda em outra loja.

`/lojistas`: diagnóstico de catálogo, itens ausentes e operações pendentes. `/lojistas atualizar`: recarrega configuração e pendências sem reiniciar. Restrito ao console ou Dono/ADM autenticado (canManageRanks). Não permite executar comandos arbitrários ou definir preços pelo cliente. Ajustes do catálogo são feitos por operação administrativa controlada no banco, seguida de atualizar.

`npc_shop_transactions` registra jogador UUID, loja, item, quantidade, direção, total e estado. Índice único impede mais de uma operação pendente por jogador, inclusive em reinício. PREPARED/APPLYING/REVIEW bloqueiam novas compras até conferência; COMPLETED/CANCELLED liberam. Recibos de moeda e itens são persistidos no playerdata, com verificação da conta CobbleDollars e salvamento. Falha incerta não gera repetição, reembolso automático ou entrega automática: UUID da operação fica na mensagem/log para conferir banco, inventário e saldo. O fechamento da janela/deslocamento antes da aplicação cancela sem movimentação. Não há transação ACID única entre PostgreSQL, conta CobbleDollars e playerdata; falhas de disco/processo nesse intervalo exigem conciliação manual. Nunca alterar um estado em REVIEW sem confirmar o que realmente foi entregue/cobrado.

## Validação

Build e teste de política: limites de quantidade/preço, variação estável, venda desabilitada e impossibilidade de preço de compra inferior à revenda. PostgreSQL isolado: migration, 78 ofertas em sete lojas, índice único de pendência, estados de revisão/conclusão/cancelamento e rejeição de estado inválido. Instalação e diagnóstico em produção devem ser registrados em HISTORICO.md. Compra/venda visual no cliente com jogador real só pode ser declarada validada após teste em jogo; não foi simulada movimentação de saldo de jogadores reais para isso.

## Catálogo atual — 1.40.0

A configuração anterior de sete lojas/78 ofertas foi substituída a pedido do dono. Agora são três NPCs por piso, numerados no nome de 1 a 9:

| Nº | Piso | Loja | Ofertas | Preço em CobbleDollars |
|---|---|---|---:|---|
| 1 | Térreo | Blocos de construção | 803 | 20–100.000 por unidade |
| 2 | Térreo | Miscelâneos, medicamentos e frutas comuns | 119 | 500–10.000 |
| 3 | Térreo | Máquinas Cobblemon | 6 | 100.000–250.000 |
| 4 | Intermediário | Poké Bolas | 46 | 200–50.000 |
| 5 | Intermediário | TMs registrados do TMCraft | 929 | 150.000 |
| 6 | Intermediário | Held Items + cinco materiais básicos Mega Showdown | 122 | 350.000–2.000.000 |
| 7 | Superior | Evolução | 52 | 100.000–1.500.000 |
| 8 | Superior | Frutas EV, proteínas e PP | 14 | 100.000–500.000 |
| 9 | Superior | Blocos CobbleFurnies | 367 | 2.000 |

Catálogo exato exportado em `catalogue-1.40.0.csv` (2.458 ofertas). As novas ofertas não têm recompra: comprar caro não cria uma fonte equivalente de dinheiro vendendo itens craftáveis/farmáveis. Dois NPCs adicionais com skins Hilbert e Rosa sem repetir as sete anteriores. Numeração cresce da esquerda para a direita, de baixo para cima. Novo NPC 6 no segundo piso, novo NPC 9 no superior; três vendedores em cada bancada. Nenhum bloco da construção foi alterado.

`npc_shop_catalogue_versions` (migration 071) registra a instalação única do catálogo gerado pelos IDs registrados e tags reais. Alterações futuras de preços no banco não são sobrescritas em cada reinício. O carregamento da loja também filtra regras de proibição, independentemente da flag enabled. Atualizar os mods não adiciona automaticamente produtos novos sem uma nova versão de catálogo.

Exclusões: Master Ball/Park Ball, mints e suas sementes/folhas, Bottle Caps, ZA Mega, itens específicos do Mega Showdown de megaevolução, cristais Z e mudança de forma; itens administrativos/sem obtenção normal e componentes de redstone não são produtos de construção. Exceções Mega Showdown: `keystone` (1.000.000), `mega_stone` (2.000.000), `blank_z` (1.500.000), `sparkling_stone_light` e `sparkling_stone_dark` (1.250.000 cada). Nenhuma Mega Stone específica ou cristal Z específico é vendido. Este trabalho reserva esses itens para futura oferta VIP; não os adiciona automaticamente ao site.

Preço de evolução é política de balanceamento, não percentual de drop: pedras mineráveis básicas 100 mil; demais pedras 200 mil; itens evolutivos comuns 400 mil; especiais 750 mil; formas de obtenção mais restritas 1,5 milhão. Conferência das fontes: [Evolution Stone](https://wiki.cobblemon.com/index.php/Evolution_Stone), [Chipped Pot](https://wiki.cobblemon.com/index.php/Chipped_Pot), [Ruins](https://wiki.cobblemon.com/index.php/Ruins), [Metal Alloy](https://wiki.cobblemon.com/index.php/Metal_Alloy). Chipped Pot tem peso inferior ao Cracked Pot nos mesmos exemplos de ruínas; Metal Alloy é craftável, por isso está abaixo do grupo máximo. Itens que evoluem um Pokémon para uma espécie nova continuam no catálogo de evolução; itens que trocam a forma de uma espécie existente ficam reservados.

Redstone: pó, tochas, repetidores, comparadores, pistões, observadores, dispensers, droppers, hopper, crafter, botões, placas de pressão e demais mecanismos da lista `ShopRestrictions` não são vendidos e a colocação direta por jogadores é negada, inclusive em Criativo. Sem exceção automática para staff. Não apaga mecanismos já existentes nem bloqueia `/setblock`/WorldEdit de administradores: isso exigiria uma alteração separada no poder administrativo. Bottle Caps: receitas com qualquer variante como ingrediente ou resultado são removidas durante load/reload; proteção adicional de entrada no RecipeManager. O servidor confirmou 14 receitas removidas. Não altera a função de aplicar o Bottle Cap diretamente em Pokémon.

A loja padrão CobbleDollars foi filtrada para 47 produtos permitidos (antes 55), com valores alinhados ao Atlas, e recarregada. Backup da configuração original junto do backup 1.40.0. Inventários personalizados de mercadores externos, se criados depois por terceiros, exigem a mesma revisão. GTS entre jogadores permanece independente.

Build/políticas e teste PostgreSQL isolado aprovados, incluindo instalação versionada idempotente, exclusão de pendências e preservação do catálogo já instalado. Serviço 1.40.0 ativo; diagnóstico: nove lojas, 2.458 ofertas, nenhum ID ausente, zero pendências. Bloqueios reais de colocação/crafting e navegação com centenas de itens ainda devem ser conferidos no cliente. Atlas Interface 1.0.1 continua compatível, sem novo JAR de cliente para esta alteração.
