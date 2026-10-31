# Construções das warps — VIP, Raid, Safari e SafariVip

Geradas por `infra/world-tools/warp-schematics.py` (Python puro, sementes fixas) em 31/10/2026. Cada uma é uma ilha flutuante de 128×56×128 na paleta Atlas (quartzo, concreto branco e ciano, carvalho escuro, blackstone polida, lanternas do mar), para colar em área vazia, longe do Lobby. A prévia vista de cima está em `*-preview.png`; posições exatas em `warps.json`.

| Arquivo | Conteúdo |
|---|---|
| `atlas-warp-vip.litematic` | Avenida iluminada, praça com fonte, pavilhão com cúpula de vidro ciano e friso dourado, quatro jardins com bétulas, bancos |
| `atlas-warp-raid.litematic` | Arena circular com anéis ciano, arquibancadas, muralha com quatro portões, pilares iluminados, cristais de ametista e pedestal central |
| `atlas-warp-safari.litematic` | Relevo natural, lago, árvores, capim alto e flores, sebe na borda, posto de guarda-parque e torre de observação |
| `atlas-warp-safarivip.litematic` | Quatro biomas (campo florido com cerejeiras, lago com ilhotas, morros rochosos, taiga nevada), chalé VIP central com friso dourado |

Todas têm a chegada ao sul, sobre o emblema de Poké Bola: posição relativa `x63 y17 z113`, olhando para o norte (yaw 180). Depois de colar em `(X, Y, Z)`, ficar nesse ponto e usar `/setwarp <nome>`.

## Colar

1. Copiar os `.litematic` para a pasta `schematics` da instância do Minecraft (Litematica já faz parte do modpack).
2. Em criativo, com OP, escolher uma área vazia, carregar o schematic, posicionar e usar o modo de colagem do Litematica.
3. Conferir a área antes: a colagem substitui os blocos do volume 128×56×128.

## Pontos de integração

- Raid: o pedestal central tem quartzo cinzelado em `x63 y19 z63`; a toca de raid fixa fica em `x63 y20 z63`.
- Safari e SafariVip: área de spawn é o terreno dentro da sebe (raio ~56 a partir de `x63 z63`). No SafariVip os quadrantes são noroeste campo florido, nordeste lago, sudoeste morros, sudeste taiga nevada.

Acesso VIP, spawns do Safari e a toca de raid rotativa ainda não foram implementados.
