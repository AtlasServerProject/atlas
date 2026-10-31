# Core 1.40.6 — login local por senha

Todos os clientes usam autenticação local, independentemente de o nome existir na Mojang. Nomes válidos: letras ASCII, números e sublinhado, de 3 a 16 caracteres. O UUID enviado pelo cliente não é usado como prova de identidade.

Contas existentes são encontradas sem distinguir maiúsculas e minúsculas e mantêm UUID/nome canônico, dados e cargos. Novas identidades usam UUID determinístico com o nome em minúsculas para evitar contas paralelas por variação de caixa. Nenhuma migração automática para identidade Premium é executada.

Contas existentes precisam de sua senha atual; /register não substitui contas antigas. Contas antigas com sentinela !premium exigem senha inicial definida no terminal pelo operador root durante a instalação. O script não imprime senhas e mantém os verificadores anteriores em backup restrito para reversão. Contas privilegiadas sem registro de autenticação bloqueiam a instalação para revisão administrativa.

A recuperação por email continua exigindo código válido enviado a um email/vínculo previamente confirmado. O módulo dev mantém seu fluxo separado por cookie autorizado. Novas conexões com a mesma identidade já conectada são recusadas sem expulsar a sessão ativa.

Validação: localAuthenticationTest, localLoginPolicyTest, remapJar; helper de instalação verificado com dados fictícios. Entrada real pelo launcher ainda depende da instalação e do teste do jogador.
