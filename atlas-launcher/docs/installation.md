# Instalação 0.4.0

Windows x64 é o alvo inicial. O launcher instala Minecraft 1.21.1, Fabric Loader 0.18.0, Java Temurin 21 e o pack Atlas 1.0.2-beta.2 com 57 mods. A versão inclui Atlas Interface 1.1.1, com o endereço stapling-gpo.tun.ply.gg.

Use Conhecer o launcher → Preparar Minecraft. Recomenda-se pelo menos 4 GB livres no disco para a instalação inicial; o instalador calcula os downloads ausentes e mantém reserva para extração. O jogo exige pelo menos 4 GB de RAM alocados, com memória disponível para o sistema. O launcher baixa o Java: não é necessário instalá-lo manualmente.

A instância fica dentro do userData do aplicativo, separada da pasta .minecraft. Saves, screenshots e arquivos pessoais não são removidos. O servers.dat e options.txt iniciais só são criados se ainda não existirem.

Downloads usam fontes oficiais, tamanho e hashes, cache conferido e retomada quando suportada pelo servidor. O pack usa manifesto Ed25519, staging, backup e journal de recuperação. Instalações concorrentes e atualizações enquanto o jogo estiver aberto são bloqueadas.

O login usa o Client ID público próprio do Atlas: consulte microsoft-login.md. Não se cadastra Client Secret. Sem Client ID, o botão Microsoft fica desabilitado; sem perfil Minecraft autenticado, Jogar fica bloqueado. Não há login por nickname liberado nesta versão.

Tokens ficam no processo principal e o cache persistido exige criptografia do sistema operacional. O renderer não recebe tokens. Logs de diagnóstico têm limite e redação de credenciais. O processo Java recebe ambiente restrito, sem herdar segredos ou opções Java arbitrárias.

A release inicial acompanha o aplicativo. Hospedagem de releases, atualização automática do launcher, SSE e instalador Windows ainda não estão integrados. O executável ainda não tem assinatura Authenticode. A chave privada de publicação permanece fora do repositório e do pacote.

O download real de um mod, do Java Windows e das oito bibliotecas nativas foi verificado nesta VM. Login real, instalação completa e execução do Minecraft em Windows ainda precisam de teste; esta VM Linux não executou os binários Windows.
