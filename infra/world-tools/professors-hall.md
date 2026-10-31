# Hall dos Professores — castelo do Lobby

Aplicado em 30/10/2026, dimensão `atlas:emerald`, entrada leste próxima de `1141 81 4062`.

O Hall existente no Atlas registra jogadores que concluíram a Pokédex. O projeto usa esse significado: não cria homenagens com nomes fictícios nem promete atualização automática dos pedestais.

## Ambientes

- Térreo: piso de quartzo com moldura de andesito, passadeira azul, palco cerimonial, bancos, recepção, estantes e Curador do Hall.
- Segundo piso: galeria de conquistas com pedestais de ametista, assentos e pontos de leitura.
- Sótão: arquivo/biblioteca com estantes altas, mesa de pesquisa coletiva e iluminação da abóbada.
- Quatro torres, três níveis cada: Pesquisa, Descobertas, Memórias e Conhecimento. Passagens internas nos dois pisos inferiores e escadas verticais apoiadas nas paredes permitem chegar ao último nível.
- Escadaria dupla de madeira escura liga os três pisos principais. Os vãos têm guarda-corpos.
- 35 lanternas comuns suspensas com correntes, flores e detalhes em dourado/ciano.

O Curador é um Easy NPC com a skin remota já utilizada pelo Professor Carvalho. Seu marcador `atlas_npc_hall_professores` utiliza o atendimento existente no Core para exibir o Hall real, com autenticação. A aparência remota depende do carregamento no cliente; posição e configuração foram conferidas no servidor. O clique deve ser confirmado por um jogador.

## Escopo e verificação

Foram alterados 923 blocos, criados nove letreiros e um NPC. Todos os blocos originais foram conferidos antes da aplicação, e os tipos resultantes foram verificados depois. Preservados os 130 blocos de vidro/janelas examinados, a fachada e o telhado. Somente aberturas internas das torres e vãos das escadas foram removidos.

A análise do mapa de colisão discretizado encontrou caminho da entrada para palco, galeria, biblioteca e os 12 ambientes das torres. É uma conferência estrutural, não substitui a inspeção visual dentro do Minecraft. Iluminação medida nos pontos centrais das áreas: 6–12 de luz de bloco. Não ficaram chunks forçados após a execução.

## Backup e reversão

Backup anterior completo das regiões afetadas:
`/home/somente/backups/lobby-emerald/professors-hall-20261030T180027Z`

- `hall-decoration.json`: estados anteriores/resultantes de cada bloco e progresso da aplicação.
- `after/region/r.2.7.mca`: fotografia da região após salvar a decoração.
- `navigation-verification.json`: resultado das verificações de acesso e luz.

Script: `infra/world-tools/decorate-professors-hall.py`.

O modo `--apply` recusa reaplicação caso o diário já exista. `--rollback` remove apenas entidades com o marcador exclusivo `atlas_professors_castle` e tenta restaurar blocos que ainda têm o tipo colocado pelo projeto. Revise alterações posteriores no castelo antes de reverter; não restaure a região inteira sobre construções mais recentes.

## Diálogo do curador

Atualização preparada em `infra/releases/atlas-professors-dialogue-1.40.5-hall.1`. Explica os registros de captura, espécies implementadas, marcos de 10%, título Professor Atlas e objetivo do Hall. Botões usam comandos existentes `/dex`, `/academia premios` e `/dex hall`. O controle de autenticação permanece obrigatório.

Instalação pendente de execução root: `sudo python3 /home/somente/dev/atlas/infra/security/deploy-professors-dialogue.py --apply`. O script valida o Core-base exato, faz backup e reinicia somente o Minecraft com reversão em caso de falha de inicialização. Somente a classe de interação dos NPCs é substituída; alterações locais de autenticação ainda não publicadas são excluídas do pacote.
