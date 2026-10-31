> Estado atual 0.4.0: autenticação, downloads e instalação foram implementados. As notas de fases anteriores abaixo são históricas. Consulte [instalação](installation.md), [cadastro Microsoft](microsoft-login.md) e [verificação](verification.md) para os limites atuais.

# Desenvolvimento

Consulte os comandos no README. `npm ci` usa o lockfile; `npm run dev` inicia Vite e Electron e encerra Vite quando a janela fecha. A interface de desenvolvimento fica acessível apenas em loopback. Abrir o Vite no navegador permite prévia visual, mas não dá acesso às configurações locais — a mensagem informa essa limitação.

O desktop não exige backend para abrir. O backend roda com Java 21 e Maven Wrapper em 8091. Sem MySQL nesta fase, não há senha/banco de demonstração. A persistência de releases com migrations será configurada na fase 4 e independente do banco de produção Atlas.

Dados locais: `app.getPath('userData')/settings.json` e diretório reservado `instances/atlas-cobblemon`. Em Windows o Electron usa o diretório de dados do aplicativo do usuário; não editar `.minecraft`. Fechar a janela termina o launcher nesta fase; a preferência de minimizar será aplicada quando existir processo Minecraft gerenciado.

Não há segredos de desenvolvimento a configurar. Ainda faltam: Client ID Microsoft aprovado, definição do login offline, catálogo oficial versionado (incluindo loader), origens de arquivos autorizadas, bucket/CDN, chaves Ed25519 do publicador, autenticação administrativa e assinatura do instalador. Não crie credenciais fictícias.

## Verificação por fase

Nesta fase: testes unitários de preferências/origem, persistência concorrente; integração HTTP do backend com health/status e negação administrativa; typecheck, build e inspeção visual desktop. As funcionalidades futuras exigem testes próprios antes de liberar Jogar. Windows precisa de validação real antes de distribuir instalador.

Electron 45 distribui o binário por instalação explícita: `npm run setup` faz o download validado pelos checksums do pacote. `npm run dev` e `npm start` executam esse preparo automaticamente. Não é necessário aprovar scripts de terceiros globalmente.

## Limitação verificada nesta VM Linux

O build e os testes unitários/HTTP passaram, mas o Electron recusou iniciar: `chrome-sandbox` não está configurado como helper de sistema e AppArmor restringe user namespaces (`unshare -Ur` retorna Operation not permitted). Não foi usado `--no-sandbox` nem alterada a política do sistema. Esta sessão não tem sudo. O teste gráfico executado foi da camada React em navegador de teste, não da janela Electron com IPC real. Para rodar nesta VM, um administrador deve configurar o suporte ao sandbox conforme a distribuição; não desative a proteção. A validação nativa Windows permanece pendente.

No Windows, abra PowerShell na pasta `atlas-launcher` e use os mesmos comandos npm. O wrapper Java é `services\backend\mvnw.cmd`. Electron escolhe o binário da plataforma durante `npm run setup`; não copie `node_modules` de Linux para Windows.
