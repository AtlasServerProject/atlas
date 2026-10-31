# Instalação 0.4.0

Windows x64 é o alvo inicial. O launcher instala Minecraft 1.21.1, Fabric Loader 0.18.0, Java Temurin 21 e o pack Atlas 1.0.2-beta.2 com 57 mods. A versão inclui Atlas Interface 1.1.1, com o endereço stapling-gpo.tun.ply.gg.

Use Conhecer o launcher → Preparar Minecraft. Recomenda-se pelo menos 4 GB livres no disco para a instalação inicial; o instalador calcula os downloads ausentes e mantém reserva para extração. Recomendam-se 4 GB de RAM para o jogo, mas esse valor não é obrigatório: o launcher permite tentar iniciar com menos memória, ajustando o limite da sessão e exibindo um erro se o Java ou o jogo realmente falhar. O launcher baixa o Java: não é necessário instalá-lo manualmente.

A instância fica dentro do userData do aplicativo, separada da pasta .minecraft. Saves, screenshots e arquivos pessoais não são removidos. O servers.dat e options.txt iniciais só são criados se ainda não existirem.

Downloads usam fontes oficiais, tamanho e hashes, cache conferido e retomada quando suportada pelo servidor. O pack usa manifesto Ed25519, staging, backup e journal de recuperação. Instalações concorrentes e atualizações enquanto o jogo estiver aberto são bloqueadas.

O login usa o Client ID público próprio do Atlas: consulte microsoft-login.md. Não se cadastra Client Secret. Sem Client ID, o botão Microsoft fica desabilitado; sem perfil Minecraft autenticado, Jogar fica bloqueado. Não há login por nickname liberado nesta versão.

Tokens ficam no processo principal e o cache persistido exige criptografia do sistema operacional. O renderer não recebe tokens. Logs de diagnóstico têm limite e redação de credenciais. O processo Java recebe ambiente restrito, sem herdar segredos ou opções Java arbitrárias.

A release inicial acompanha o aplicativo. Atualização automática do executável, SSE e instalador Windows ainda não estão integrados. O executável ainda não tem assinatura Authenticode. A chave privada de publicação permanece fora do repositório e do pacote.

O download real de um mod, do Java Windows e das oito bibliotecas nativas foi verificado nesta VM. Login real, instalação completa e execução do Minecraft em Windows ainda precisam de teste; esta VM Linux não executou os binários Windows.

## Atualizações 0.5.0

O aplicativo consulta o manifesto assinado no GitHub oficial ao abrir e a cada cinco minutos, quando não está instalando nem executando o jogo. Também há Buscar atualizações na tela Atualizações. Instalar a versão nova continua sendo uma ação do jogador. Arquivos válidos são reaproveitados e o mecanismo de staging/rollback existente faz a substituição dos arquivos gerenciados.

Cada candidato exige assinatura Ed25519 válida, mesmo pack/canal, versão compatível do launcher e ausência de downgrade ou alteração silenciosa da mesma versão. O último catálogo aceito é armazenado localmente com assinatura; no reinício ele e o recibo instalado são revalidados. Uma falha de rede preserva o catálogo anterior.

Fonte inicial: arquivo release.json da branch codex/configure-atlas-docs-submodule do repositório AtlasServerProject/atlas, via raw.githubusercontent.com. A consulta pública real foi testada. Se o repositório ficar privado, a consulta anônima falhará: será necessário migrar esse manifesto público para uma hospedagem própria e atualizar o endereço fixo no launcher. Tokens GitHub não são distribuídos aos jogadores. A chave privada de assinatura continua fora do aplicativo.

Esta etapa atualiza o catálogo e o modpack, não o executável do launcher. A nova versão remota com conteúdo diferente foi exercitada por fixtures assinadas nos testes; a fonte pública atualmente entrega o mesmo pack 1.0.2-beta.2.

## Perfil offline 0.6.0

Autorizado para o servidor Atlas, que possui sua própria autenticação. O nickname é validado no main; o UUID usa o algoritmo OfflinePlayer da edição Java. O perfil não contém token Microsoft, não afirma propriedade de uma conta e é revogado ao sair. O nick deve corresponder ao usado no servidor. Não substitui a senha de /login e não concede permissão administrativa. Na próxima abertura do launcher, selecione novamente o perfil.

A inicialização revalida os arquivos antes de abrir Java. Corrigida a guarda de concorrência que bloqueava essa verificação interna quando a flag de inicialização estava ativa. Logs offline não tratam o valor convencional 0 como segredo, preservando os números dos diagnósticos.

A fonte GitHub da versão 0.5.0 foi substituída pelo site oficial: /launcher/modpack.json e /launcher/latest.json. A distribuição não depende da visibilidade dos repositórios. As partes estáticas têm hashes individuais, o ZIP completo tem SHA-256 e os metadados são assinados com Ed25519. Não há execução automática de downloads.

## Instalação única 0.7.0

A partir de 0.7.0 use o instalador Setup-x64.exe em vez do ZIP. Ele instala somente o aplicativo em LocalAppData/Programs/AtlasLauncher e conserva a instância existente em userData. Não exige configuração de Microsoft/cliente ou privilégios administrativos. As consultas de versão continuam no site oficial. O novo feed de instaladores é /launcher/windows/latest.json e o antigo feed ZIP permanece para compatibilidade de distribuição.

A instalação gerenciada é reconhecida por marker com appId e pelo caminho exato no perfil do usuário. Somente esse modo aplica automaticamente os instaladores futuros. Cada executável é conferido após o download e imediatamente antes de executar; arquivos do renderer nunca definem caminho, PID, comando ou parâmetros arbitrários. O processo de atualização aguarda a saída do launcher e tem backup/rollback de ativação. A aplicação não é realizada durante o jogo. Desinstalar remove programa/atalhos, preservando dados locais do Minecraft.
