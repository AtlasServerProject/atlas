# Verificação 0.4.0 — 27/10/2026

- TypeScript, build e formatação verificados.
- 45 testes automatizados passaram e cobrem manifesto assinado, integridade, retomada, cancelamento, rollback, caminhos, ZIP, autenticação simulada, cofre, concorrência e ambiente Java.
- As 56 fontes externas responderam à consulta. Um mod real foi baixado e conferido por SHA-256.
- Plano real Minecraft/Fabric resolvido: 3.951 arquivos, 63 entradas de classpath e oito bibliotecas nativas Windows.
- Java Windows e as oito bibliotecas nativas baixados e extraídos com verificações de integridade, CRC e caminhos. Nenhum binário Windows foi executado nesta VM.
- Renderer exercitado em navegador com ponte exclusiva de teste: catálogo real de 57 mods, busca, instalação/cancelamento, autorização simulada e bloqueio de Jogar sem conta.
- Backend não alterado; seus quatro testes HTTP pertencem à verificação anterior.

Pendentes: Client ID próprio do Atlas, autorização real Microsoft/Minecraft, DPAPI em Windows, instalação completa e execução do jogo em Windows. A janela Electron nativa não foi validada nesta VM por restrição do sandbox Linux; a proteção não foi desativada.

O ZIP é uma distribuição para teste, sem instalador ou assinatura Authenticode. Não houve implantação ou reinício dos serviços de produção. npm audit não substitui auditoria de segurança.

Pacote Windows 0.4.0 gerado: PE x64, ASAR, três vídeos locais e integridade ZIP conferidos; SHA-256 em arquivo separado.

## Correção 0.4.1 — 28/10/2026

ENOTDIR reproduzido no Electron ao tentar mkdir dentro de app.asar. Recursos incluídos agora são lidos sem criação de diretório; caminhos graváveis da instância mantêm as validações. Regressão exercitada no runtime Electron com ASAR real do pacote Windows, manifesto de teste assinado e JAR incluído: instalação e SHA-256 passaram. Não substitui execução do jogo em Windows.

## Interface e atualizações 0.5.0 — 28/10/2026

Botão principal único sem seta, estados instalar/jogar, foco de teclado e versão do topo derivada da mesma constante do restante do app. 48 testes automatizados e build passaram. Consulta real do manifesto público GitHub passou pela verificação de assinatura e versão. Testes adicionais rejeitam assinatura inválida, downgrade, mudança de canal/conteúdo na mesma versão, launcher incompatível, respostas excessivas e redirecionamento externo. Atualização não instala automaticamente. Login Microsoft permanece pendente.

## Modo offline e fonte oficial 0.6.0 — 28/10/2026

53 testes automatizados e build passaram. Novos testes cobrem nick inválido, UUID Java conhecido, separação da identidade Microsoft, logout, assinatura de atualização do aplicativo, limites/caminhos, montagem de partes e rejeição de ZIP com hash final incorreto. Renderer exercitado com ponte de teste: entrar por nickname, botão Jogar habilitado, apresentação como offline e bloqueio após sair. Ainda falta execução real do Java/Minecraft no Windows. O novo ZIP foi conferido por integridade ZIP e SHA-256.

Publicação 0.6.0 no Cloudflare Pages concluída. Verificação pública em www.atlascobblemon.com.br/launcher: manifestos do launcher e pack assinados, dez partes baixadas via HTTPS e conferidas individualmente, ZIP completo SHA-256 compatível e atualização detectada para versão anterior. Página pública verificou assinatura Ed25519 no Chromium. Deploy: 9ae38276.atlas-cobblemon.pages.dev. O teste não executou binários Windows.

## Memória 0.6.1 — 28/10/2026

Removida a exigência incorreta de ter o Xmx inteiro livre antes de iniciar, preservando a capacidade física e um mínimo de memória disponível para iniciar. Java continua com Xms512M. O limite da sessão é reduzido quando apropriado, sem alterar a preferência persistida. Perfis com menos de 2 GiB disponíveis ou capacidade física insuficiente para heap de 4 GiB continuam bloqueados com números e orientação explícitos. Configurações mostram memória total/disponível e um botão de valor recomendado. 57 testes passaram; novos casos cobrem heap alto, baixa disponibilidade, capacidade física e memória inicial menor que o limite. Interface de recomendação e limpeza do prefixo técnico IPC verificadas em navegador com ponte de teste. A abertura real no Windows depende da validação pelo jogador.

## Login 0.6.2 — 28/10/2026

Removidos o divisor “enquanto isso”, o botão “Conhecer o launcher” e sua legenda. Entrada por perfil offline/Microsoft preservada. Build e TypeScript passaram; ZIP Windows conferido, incluindo PE, ASAR e três vídeos.

## Conexão 0.6.3 — 28/10/2026

Battle Positions ausente identificado pela tela de oito registros desconhecidos. Comparados arquivo original mods.zip e servidor: bytes e SHA-256 idênticos. Novo manifesto Ed25519 beta.3 inclui 58 mods, exige launcher 0.6.3 e conserva RCT API. Teste do catálogo agora exige Battle Positions, RCT API e verifica os hashes de todos os JARs incluídos. 57 testes e build passaram. JAR Battle Positions extraído do ASAR Windows empacotado e hash conferido contra a cópia do servidor. ZIP verificado. Conexão real no Windows ainda depende de teste do jogador.

## Ícone Minecraft 0.6.4 — 28/10/2026

Atlas Interface 1.1.2 aplica o ícone GLFW a partir da logo Atlas em quatro tamanhos. Build do cliente passou; PNGs e callback presentes no JAR foram inspecionados. Pack beta.4 conserva Battle Positions e substitui a versão anterior do Atlas Interface. 57 testes do launcher e build passaram; ZIP verificado. Ícone real na barra de tarefas Windows ainda depende de teste do jogador.

## Instalador e atualização automática 0.7.0 — 28/10/2026

61 testes automatizados passaram: localização/marker por usuário, PID/argumentos fixos sem shell, bloqueio com jogo/operações ativos, instalador schema 2, download automático simulado e recusa de executável alterado antes de aplicar. Build TypeScript/renderer/main passou. NSIS 3.10 compilou instalador de usuário com staging/backup e espera do PID. Payload AtlasLauncher.exe e app.asar extraído do instalador foi comparado por tamanho e SHA-256 ao pacote original: idêntico. Não foram executados binários Windows nesta VM. Instalação nativa e atualização real entre duas versões continuam pendentes de teste no Windows.

Publicação 0.7.0: site oficial servindo /launcher/windows/latest.json com schema 2 e assinatura verificada. Todas as dez partes foram baixadas do domínio oficial e conferidas individualmente; SHA-256 do instalador completo bateu. Fluxo do navegador montou o instalador e emitiu download com nome Setup-x64.exe, sem execução. Guia Como jogar atualizado e conferido no domínio público. Deploy fe45e633.atlas-cobblemon.pages.dev.

## Marca do instalador 0.7.1 — 28/10/2026

A interface Modern UI do NSIS substituía as diretivas Icon/UninstallIcon pelos padrões. Corrigido com MUI_ICON e MUI_UNICON. Conferência do recurso primário RT_GROUP_ICON do EXE confirmou todos os sete PNGs Atlas idênticos ao ICO original (NSIS reordena tamanhos; 0 representa 256 pixels). O instalador anterior foi rejeitado pela mesma checagem. O build do instalador agora executa essa validação antes de aceitar o artefato. Build TypeScript/Electron e compilação NSIS passaram. Nenhuma alteração de runtime do atualizador nesta versão, além da versão publicada.

## 0.7.8 — Diagnósticos acionáveis

- Interface apresenta código estável, evidência disponível, responsável pela verificação e instruções específicas; permite copiar a orientação e abrir a pasta de logs.
- Runtime observa stdout/stderr enquanto Minecraft continua aberto. Atlas Interface 1.1.3 identifica a tela real de desconexão e emite somente códigos fixos, sem copiar o motivo remoto ou dados de contas.
- Sessão inválida em modo offline recebe orientação de verificar a política do servidor; em modo Microsoft, renovar a sessão. A mensagem não afirma que um nick é premium sem confirmação.
- Casos reconhecidos: voo bloqueado, registros/mods incompatíveis, timeout/host inacessível, conexão interrompida, memória real, Java/OpenGL, pacote de recursos, disco cheio, arquivos bloqueados, conflito arquivo/pasta e integridade.
- Erros desconhecidos mantêm classificação inconclusiva e orientam coleta de evidências. Texto bruto de exceções não vai para o aviso público. A classificação não remove proteções de arquivos ou autenticação.
- 75 testes passaram; testes novos cobrem classificação, ausência de segredos/caminhos na orientação, fragmentação da saída do processo, última linha incompleta e exclusão de chat como evidência.
- TypeScript e build Windows concluídos. Ícone do instalador validado em sete tamanhos. Prévia Chromium confirmou visibilidade e fechamento do aviso sem reaparecer no polling.
- Modpack assinado `1.0.2-beta.5`, mínimo Launcher `0.7.8`, mantém 58 mods e troca somente Atlas Interface 1.1.2 por 1.1.3. O cliente não recebeu outros recursos novos.
- Teste nativo Windows de desconexão real ainda deve ser confirmado por um jogador. A detecção depende da evidência registrada ou da nova versão do Atlas Interface.
