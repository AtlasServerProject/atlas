# Construções das warps — VIP, Raid, Safari e SafariVip

Geradas por `infra/world-tools/warp-schematics.py` (Python puro, sementes fixas) em 31/10/2026. VIP, Raid e Safari são ilhas flutuantes de 128×56×128; a SafariVip é uma ilha redonda de 192×56×192 com mar próprio. Todas usam a paleta Atlas (quartzo, concreto branco e ciano, carvalho escuro, blackstone polida, lanternas do mar) e devem ser coladas em área vazia, longe do Lobby. Prévias: `*-preview.png` (de cima) e `*-view.png` (vista do sul, lado da chegada). Posições exatas em `warps.json`.

| Arquivo | Conteúdo |
|---|---|
| `atlas-warp-vip.litematic` | Avenida iluminada, praça com fonte, pavilhão com cúpula de vidro ciano e friso dourado, Shopping VIP de quatro andares com terraço (noroeste) e seis currais de EV em redomas de vidro (leste) |
| `atlas-warp-raid.litematic` | Arena circular com anéis ciano, arquibancadas, muralha com quatro portões, pilares iluminados, cristais de ametista e pedestal central |
| `atlas-warp-safari.litematic` | Relevo natural, lago, árvores, capim alto e flores, sebe na borda, posto de guarda-parque e torre de observação |
| `atlas-warp-safarivip.litematic` | Ilha redonda no mar com 24 biomas principais do overworld em setores orgânicos, montanha nevada com duas cavernas, rio, Centro Pokémon Atlas em cúpula de vidro no centro, estátuas de Pikachu, Snorlax e Poké Ball, píer de chegada |

Chegada ao sul, sobre o emblema de Poké Bola, olhando para o norte (yaw 180): posição relativa `x63 y17 z113` (SafariVip: `x96 y17 z168`). Depois de colar em `(X, Y, Z)`, ficar nesse ponto e usar `/setwarp <nome>`.

## Colar

1. Copiar os `.litematic` para a pasta `schematics` da instância do Minecraft (Litematica já faz parte do modpack).
2. Em criativo, com OP, escolher uma área vazia, carregar o schematic, posicionar e usar o modo de colagem do Litematica.
3. Conferir a área antes: a colagem substitui os blocos do volume inteiro (128×56×128; SafariVip 192×56×192).

## Pontos de integração

- Raid: o topo do pedestal é um 3×3 de quartzo cinzelado (`x62..64 y19 z62..64`) com o bloco central em `x63 y19 z63`; a toca de raid fixa fica sobre ele, em `x63 y20 z63`.
- Safari: área de spawn é o terreno dentro da sebe (raio ~56 a partir de `x63 z63`).
- SafariVip: cada coluna 4×4 recebe seu bioma pelo `/fillbiome`; caixas em `safarivip-biomes.json`.


## VIP: Shopping VIP e currais de EV

O jardim noroeste, o mais próximo da cúpula, virou o **Shopping VIP**: uma loja de departamentos de quatro andares em quartzo e vidro ciano, com o letreiro VIP dourado na fachada leste, escadas em zigue-zague no lado norte e um terraço com cerejeiras no topo. Cada andar tem um balcão no lado sul, com o lugar do lojista atrás. Os outros três jardins saíram.

| Andar | Loja | Tag do NPC (Easy NPC) | Lugar do lojista (relativo) |
|---|---|---|---|
| 1º | Bolas e tampinhas | `atlas_npc_vip_store_1` | `x25 y17 z49` |
| 2º | Mints | `atlas_npc_vip_store_2` | `x25 y22 z49` |
| 3º | Formas e relíquias | `atlas_npc_vip_store_3` | `x25 y27 z49` |
| 4º | Megapedras e cristais Z | `atlas_npc_vip_store_4` | `x25 y32 z49` |

Os lojistas vendem os itens que as lojas comuns bloqueiam por serem VIP (Master Ball, Park Ball, tampinhas, mints, placas, memórias, drives, orbes, megapedras, cristais Z, braceletes e anéis). Só VIP 1 ou superior compra, em qualquer mundo, e não há revenda para a loja. Atlas Core `1.40.5+evvip.1`.

No lado leste, ligado à praça por um corredor, ficam os **currais de EV**: seis redomas de vidro em volta de um pátio, cada uma com a cor do seu atributo e a porta voltada para o pátio.

| Curral | Cor | Centro (relativo) |
|---|---|---|
| HP | red | `x88 y17 z70` |
| Ataque | orange | `x88 y17 z56` |
| Defesa | yellow | `x100 y17 z49` |
| Ataque Especial | blue | `x112 y17 z56` |
| Defesa Especial | lime | `x112 y17 z70` |
| Velocidade | pink | `x100 y17 z77` |

Dentro de cada redoma, o módulo Currais de EV do Atlas Core mantém até 4 Pokémon selvagens **incapturáveis** (nível 30 a 50), escolhidos entre os que rendem 3 EVs daquele atributo e nada mais. A lista vem dos dados de espécie do Cobblemon instalado, sem lendários. Derrotados voltam em 20 s se houver jogador a até 48 blocos; os que saem são devolvidos; outros selvagens que surgirem dentro da redoma são removidos. A configuração com coordenadas absolutas sai de `python3 infra/world-tools/warp-schematics.py <saída> --vip-origin X Y Z --vip-world <dimensão>` (`atlas-ev-corrals.json`), e vai para `config/atlas/ev-corrals.json` no servidor; depois, `/currais recarregar`.

## SafariVip: ilha dos biomas

Ilha redonda (raio ~80) num mar circular de raio 93, contido por um anel de `barrier` invisível. No centro fica o Centro Pokémon Atlas: cúpula de vidro ciano com nervuras de quartzo, faixa ciana e dourada, quatro portas, PCs, máquina de cura e o emblema de Poké Bola no piso, sobre uma praça de quartzo. Os biomas formam uma roda de clima com bordas irregulares:

| Direção | Biomas |
|---|---|
| Norte | montanha: `jagged_peaks` (cume nevado) e `stony_peaks`, com `lush_caves` e `dripstone_caves` em câmaras dentro dela (túneis voltados para a praça) |
| Nordeste | `cherry_grove`, `meadow`, `river` descendo da montanha até o mar |
| Leste | `jungle`, `savanna`, `beach`, `warm_ocean` |
| Sudeste | `desert` (santuário de arenito), `badlands` (mesas), estátua de Poké Ball numa ilhota |
| Sul | `plains`, estátua do Pikachu, avenida de quartzo, plataforma de chegada e píer |
| Sudoeste e oeste | `forest`, `flower_forest` (estátua do Snorlax), `birch_forest`, `dark_forest`, `swamp` |
| Noroeste | `taiga`, `snowy_taiga`, `snowy_plains`, `ice_spikes` |
| Em volta | `ocean` |

Ficaram de fora os biomas do Nether e do End e as variantes menores do overworld.

O schematic leva só os blocos. Depois de colar, os biomas são aplicados com `/fillbiome`: 287 caixas (colunas 4×4 agrupadas, cada uma abaixo do limite de 32.768 blocos do comando), mais as duas cavernas em 3D, aplicadas por último. Os comandos absolutos saem de `python3 infra/world-tools/warp-schematics.py <saída> --safarivip-origin X Y Z`. Colar com X e Z múltiplos de 4 (para as colunas 4×4 coincidirem com as do jogo) e Y=45, para a superfície ficar em Y=61 e os Pokémon em Y=62.

Cobertura calculada por `infra/world-tools/spawn-coverage.py --zones safarivip-zones.json`, que cruza as regras de spawn instaladas (Cobblemon 1.8.2, Mega Showdown, presets e tags de bioma/bloco) com o que cada bioma da ilha realmente contém: **806 de 916 espécies implementadas (88,0%)**. É uma estimativa por regra, sem teste em jogo, e supõe os pés em Y=62 (os morros ficam mais altos). A chance real de cada espécie depende do peso e da raridade da regra.

Detalhes que existem por causa de regras específicas: concreto só no Centro Pokémon (o preset "wild" bloqueia spawns a até 4 blocos de concreto; as estátuas são de lã e terracota); para-raios, bolo e PC na praça; árvore saccharine e bolo na Meadow; frutas do Cobblemon na Birch Forest; abóboras em Plains e Taiga; lago de pesca na Dark Forest; kelp e algas no oceano, corais no warm_ocean; coqueiros na Beach; ruína e cobblestone na Jungle; ruína de tijolos e minérios (inclusive diamante) na Dripstone Caves; poça, argila e glow berries na Lush Caves; sem lanternas perto da neve.

Acesso VIP às warps, spawns próprios do Safari e a toca de raid rotativa ainda não foram implementados.
