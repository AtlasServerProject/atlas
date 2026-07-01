# Arquitetura dos Lobbys do Atlas

## Fluxo inicial

```text
Entrada
  ↓
Auth Lobby
  ↓
Login, registro ou autenticação Premium
  ↓
Bússola de servidores
  ↓
Lobby Emerald
  ↓
Survival Emerald
```

O Auth Lobby não envia o jogador automaticamente ao Emerald. Após autenticar, o
jogador permanece no mesmo lobby e recebe acesso ao seletor de servidores.

## Auth Lobby

Responsável exclusivamente pela entrada e autenticação. Antes do login, o Atlas
bloqueia movimentação, chat e comandos, exceto `/login` e `/register`. As demais
proteções previstas incluem inventário, blocos, dano e interações.

O mapa `Lobby Hub` foi adotado como Auth Lobby. Antes da implantação, foram
removidos dados legados de jogadores, inventários, Pokémon, Pokédex, estatísticas
e advancements. Mensagens promocionais e links externos também foram removidos.

Spawn global inicial:

```text
X: 646
Y: 83
Z: 3535
Orientação: oeste (90°)
```

O raio aleatório do spawn está desativado. Toda conexão é teleportada para o
centro do bloco (`646.5 83 3535.5`), inclusive quando o jogador já possui uma
posição anterior salva.

## Seletor

Depois da autenticação, uma bússola abrirá o menu de servidores. A primeira opção
será o Emerald. O seletor será a fronteira entre a autenticação global e os
servidores de gameplay, permitindo substituir o transporte local por uma conexão
via proxy no futuro.

## Lobby Emerald

O Lobby Emerald será o hub do primeiro servidor do Atlas. Ele concentrará acesso
ao Survival Emerald, NPCs, crates, rankings, tutorial, loja, eventos, scoreboard
e navegação.

## Evolução para Atlas Network

O lançamento terá somente o Emerald. Uma expansão futura poderá adicionar outros
servidores mantendo globais conta, autenticação, UUID, Premium, VIP, ranks,
amigos e Discord. Economia, Pokémon, GTS, crates, eventos e progressão continuarão
isolados por servidor.
