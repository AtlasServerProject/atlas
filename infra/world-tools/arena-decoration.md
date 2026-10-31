# Arena Atlas — 30/10/2026

Arena existente no Lobby (`atlas:emerald`), entrada leste próxima de `1162 83 4109`.

Aplicadas e verificadas 143 alterações de blocos e sete letreiros: duas posições de treinador (azul/vermelho), iluminação embutida nos corredores, detalhes ciano na entrada e na fachada das arquibancadas, nichos decorativos com dourado/ametista e quatro lanternas suspensas. Preservados mosaico central, linhas brancas do campo, vidros e estrutura do estádio. Nenhum NPC novo foi criado.

Backup e diário de blocos:
`/home/somente/backups/lobby-emerald/arena-20261030T185516Z`

Execução: `infra/world-tools/decorate-arena.py`. Reutiliza o editor de console com conferência dos estados anteriores e reversão. O diário usa o nome genérico `hall-decoration.json` por compatibilidade com esse editor; o marcador exclusivo da arena é `atlas_arena_decoration`.

## Warp preparada, instalação pendente

`/warp arena`: `1155.5 83 4109.5`, olhando para oeste (`yaw 90`). Piso e dois blocos de altura livres foram conferidos no servidor. A criação preserva os demais destinos públicos/privados.

Para gravar o catálogo pertencente ao usuário isolado e recarregá-lo:
`sudo python3 /home/somente/dev/atlas/infra/security/configure-arena-warp.py --apply`

O script salva backup do catálogo, reinicia o Minecraft e reverte se a inicialização falhar. Não modifica a decoração nem instala outro Core.
