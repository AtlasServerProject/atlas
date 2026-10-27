> Estado atual 0.4.0: autenticação, downloads e instalação foram implementados. As notas de fases anteriores abaixo são históricas. Consulte [instalação](installation.md), [cadastro Microsoft](microsoft-login.md) e [verificação](verification.md) para os limites atuais.

# Segurança — fase 1

Renderer sem Node, sandbox e contextIsolation habilitados, webSecurity preservado. Preload expõe somente bootstrap, salvar preferências, abrir o site oficial fixo e minimizar/maximizar/fechar a janela. Não expõe IPC bruto, fs, shell, comandos ou URLs arbitrárias. Main exige o WebContents e frame principal da janela e URL exata. Toda configuração é revalidada no main, inclusive limites de RAM/resolução e campos desconhecidos. Preferências não contêm tokens ou senhas. Gravações são serializadas e renomeadas atomicamente.

Navegação, webviews, popups e permissões do navegador são negados. CSP restringe scripts à própria origem (HMR em desenvolvimento requer script inline); estilo inline é permitido para o runtime de desenvolvimento. Nenhum script remoto é carregado. Apenas URL local fixa de desenvolvimento é aceita; em build carrega o arquivo local. Variável de desenvolvimento é ignorada em aplicativo empacotado. Não usar `--no-sandbox` em ambiente de usuário.

Backend vinculado ao loopback, sem conta padrão, nega demais rotas por padrão, CSRF preservado, sem CORS aberto, sem detalhes do Actuator ou stack traces públicos. Ainda não há banco, upload, publicação, SSE ou autenticação implementados. Não é um serviço pronto para exposição pública.

Limites: o diretório de instalação nesta fase é fixo dentro de userData e não é escrito pelo instalador (ainda inexistente). Preferências não lançam Minecraft. RAM limita a memória total com reserva; na fase 5 será preciso reavaliar memória disponível imediatamente antes de iniciar e avisar sobre requisitos mínimos do pack. Credenciais Microsoft exigirão cofre do SO, não JSON/localStorage; autenticação oficial e política offline precisam de definição real.

Para distribuição Windows: assinatura de código e updater autenticado, testes em máquina limpa e auditoria das dependências. Certificados, chaves privadas e credenciais nunca fazem parte do frontend, dos assets ou do Git. Nenhuma alegação de proteção absoluta ou auditoria completa é feita por esta fundação.

## Prévia Windows 0.2.0

Janela sem moldura nativa, com controles restritos por enum e validação de emissor no main. O usuário pode fechar, minimizar e restaurar/maximizar sem expor operações genéricas. O pacote contém somente o build, metadados públicos e runtime Electron; não inclui fontes do backend, .env, bancos ou dados do servidor. ASAR organiza o código, não é criptografia nem substitui assinatura de distribuição. A prévia ainda não tem Authenticode, instalador ou auto-update; exige teste nativo Windows.

## Fundação 0.3.0

Site e IP centralizados em `shared/project.ts`; o processo principal continua abrindo somente o HTTPS fixo do site. A CSP agora permite mídia apenas da própria aplicação. Nenhuma origem remota foi liberada para reproduzir os vídeos, que acompanham o pacote. Os novos validadores de manifesto estão cobertos por testes e ainda não executam download, escrita ou remoção de arquivos.
