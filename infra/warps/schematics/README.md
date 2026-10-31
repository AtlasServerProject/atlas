# Construções das warps — VIP, Raid, Safari e SafariVip

Geradas por `infra/world-tools/warp-schematics.py` (Python puro, sementes fixas) em 31/10/2026. Cada uma é uma ilha flutuante de 128×56×128 na paleta Atlas (quartzo, concreto branco e ciano, carvalho escuro, blackstone polida, lanternas do mar), para colar em área vazia, longe do Lobby. A prévia vista de cima está em `*-preview.png`; posições exatas em `warps.json`.

| Arquivo | Conteúdo |
|---|---|
| `atlas-warp-vip.litematic` | Avenida iluminada, praça com fonte, pavilhão com cúpula de vidro ciano e friso dourado, quatro jardins com bétulas, bancos |
| `atlas-warp-raid.litematic` | Arena circular com anéis ciano, arquibancadas, muralha com quatro portões, pilares iluminados, cristais de ametista e pedestal central |
| `atlas-warp-safari.litematic` | Relevo natural, lago, árvores, capim alto e flores, sebe na borda, posto de guarda-parque e torre de observação |
| `atlas-warp-safarivip.litematic` | Tabuleiro 8×8 de zonas 16×16, uma para cada um dos 64 biomas vanilla, com terreno típico; praça urbana e chalé VIP no centro |

Chegada ao sul, sobre o emblema de Poké Bola, olhando para o norte (yaw 180): posição relativa `x63 y17 z113` (SafariVip: `x63 y17 z121`). Depois de colar em `(X, Y, Z)`, ficar nesse ponto e usar `/setwarp <nome>`.

## Colar

1. Copiar os `.litematic` para a pasta `schematics` da instância do Minecraft (Litematica já faz parte do modpack).
2. Em criativo, com OP, escolher uma área vazia, carregar o schematic, posicionar e usar o modo de colagem do Litematica.
3. Conferir a área antes: a colagem substitui os blocos do volume 128×56×128.

## Pontos de integração

- Raid: o pedestal central tem quartzo cinzelado em `x63 y19 z63`; a toca de raid fixa fica em `x63 y20 z63`.
- Safari: área de spawn é o terreno dentro da sebe (raio ~56 a partir de `x63 z63`).
- SafariVip: cada zona 16×16 recebe seu bioma pelo `/fillbiome`; zonas listadas em `warps.json` (`biome_cells`).


## SafariVip — 64 biomas

O schematic leva só os blocos. O bioma de cada zona é aplicado depois de colar, com `/fillbiome` (comandos absolutos gerados por `python3 infra/world-tools/warp-schematics.py <saída> --safarivip-origin X Y Z`, um por zona, dentro do limite de volume do comando). Colar com a origem alinhada a múltiplos de 16 em X/Z e Y=45, para a superfície ficar em Y=61 e os Pokémon em Y=62: atende regras com `minY 62` e com `maxY 62`.

Cobertura calculada por `infra/world-tools/spawn-coverage.py --zones safarivip-zones.json`, que cruza as 5.226 regras de spawn instaladas (Cobblemon 1.8.2, Mega Showdown, presets e tags de bioma/bloco) com o que cada zona realmente contém: **855 de 916 espécies implementadas (93,3%)**. Fora: 59 espécies sem spawn natural (lendárias/míticas de evento), Feebas e Milotic (pesca com condição rara). Estimativa por regra, não teste em jogo; a chance real de cada espécie depende do peso e da raridade da regra.

Detalhes que existem por causa de regras específicas: concreto só na praça central e numa escultura da zona Grove (o preset "wild" bloqueia spawns a até 4 blocos de concreto); para-raios, bolo e PC na praça; árvore saccharine e bolo na Meadow; frutas do Cobblemon na Birch Forest; abóboras em Plains e Taiga; kelp nos oceanos; árvores na Beach; lago na Dark Forest (pesca); ruína de tijolos, minérios e diamante na Dripstone Caves; santuário coberto de arenito no Desert. Lava só no centro das zonas do Nether, cercada e a 5+ blocos das bordas; sem lanternas junto às zonas de neve.

Acesso VIP, spawns próprios do Safari e a toca de raid rotativa ainda não foram implementados.
