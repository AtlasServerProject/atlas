# Atlas Interface 1.1.2

Mod de cliente para Minecraft 1.21.1, Fabric Loader >=0.17.3, Java 21 e Fabric API. Não instalar Atlas Core no cliente: somente atlas-interface-1.1.2.jar.

Tela própria do Atlas Mart: categorias separadas por NPC, abas Comprar/Vender, busca, ícones originais dos itens instalados, lista rolável, quantidade, total, saldo e confirmação. Reapresenta os menus Atlas Core >=1.39.1 existentes e envia cliques vanilla; preço/quantidade/saldo, proximidade e entrega continuam validados pelo servidor. Não adiciona protocolo de compra que aceite preço do cliente. Jogadores sem este mod continuam usando o menu de baú.

Tema azul-escuro/ciano dos botões vanilla, marca no menu principal e menu de pausa. Não substitui a tela de batalha Cobblemon nem o inventário dos Pokémon. Outros resource packs podem sobrepor os sprites dos botões conforme sua prioridade.

Instalação: feche o jogo, copie o JAR para a pasta mods da instância Atlas no launcher e abra novamente. Fabric API já faz parte do modpack. Não usar Forge/NeoForge ou Minecraft de outra versão. Para remover, feche o jogo e retire somente esse JAR; não contém mundos, contas, banco ou segredos.

Teste em jogo: entrar no Atlas, autenticar-se, sair do Criativo, clicar no balconista; conferir abas/busca/rolagem e confirmar compra/venda de uma unidade. Testar falta de saldo, falta de espaço, fechar no Esc e reconectar. Servidor 1.39.1 já instalado; não precisa reiniciá-lo para adicionar o mod ao cliente.

Build: ./gradlew build. Código próprio e sprites de interface desenhados por código. Sem imagens ou classes do Pixelmon/CobbleDollars incluídas. Compilação/inspeção do JAR verificadas; validação visual no Minecraft com jogador real ainda pendente.

## 1.1.0 — Menu principal Atlas

Fundo original de ruínas azuis gerado para o Atlas, logo original, partículas leves, moldura ciano e botões reais. Jogar Agora inicia a conexão em jogar.atlascobblemon.com.br, Servidores abre o multiplayer, Opções preserva todas as configurações vanilla, Sair encerra o jogo. Singleplayer fica no canto inferior esquerdo e abre a seleção/criação de mundos vanilla. Respeita a permissão de multiplayer da conta. Mantém as lojas, quantidade rápida e scoreboard abaixado das versões anteriores.

Substitua qualquer atlas-interface-1.x.jar anterior por atlas-interface-1.1.0.jar, com o jogo fechado. Não instalar no servidor. Não é necessário alterar o Atlas Core.

Testado com execução real Minecraft 1.21.1/Fabric em display virtual isolado a 1280×720: renderização do fundo/logo, abertura de Opções, retorno, fluxo Singleplayer e Sair. Ajustes geométricos conferidos para alturas GUI 180/200/240/270/360/540. Não foi realizado login no servidor Atlas durante esse teste; compatibilidade com todo o modpack ainda deve ser conferida pelo usuário. Preview real em downloads/Atlas-Menu-Principal-Previa.png.

## 1.1.1 — Endereço atual do Atlas

O botão Jogar Agora usa `stapling-gpo.tun.ply.gg`, consistente com o Atlas Launcher 0.4.0. Mesma interface, protocolo de lojas e compatibilidade Minecraft 1.21.1/Fabric/Java 21 da versão anterior. Não requer atualização do Atlas Core ou reinício do servidor.

## 1.1.2 — Ícone da janela

Aplica o ícone Atlas à janela GLFW e à entrada da barra de tarefas do Windows no evento CLIENT_STARTED. Os PNGs de 16, 32, 48 e 256 pixels são extraídos sem alterações do ICO existente do Atlas. Buffers nativos são liberados após a chamada; falha conserva o ícone padrão e registra aviso. Build Gradle passou e recursos/registro do callback foram inspecionados no JAR. Validação visual no Windows fica pendente do jogador.
