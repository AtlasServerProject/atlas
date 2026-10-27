> Estado atual 0.4.0: autenticação, downloads e instalação foram implementados. As notas de fases anteriores abaixo são históricas. Consulte [instalação](installation.md), [cadastro Microsoft](microsoft-login.md) e [verificação](verification.md) para os limites atuais.

# Arquitetura e análise — 27/10/2026

## Encontrado

O monorepo Atlas já contém `atlas-api` (Spring Boot/PostgreSQL), `atlas-web` (Angular), `atlas-core` e `atlas-client` (Fabric/Java), bot e infraestrutura. Não havia launcher desktop. Há alterações preexistentes em outros componentes; esta fase não as modifica nem implanta serviços. A API existente permanece independente: o novo backend usa outra porta e não suas credenciais.

Minecraft 1.21.1, Fabric e Java 21 foram confirmados nos arquivos existentes. Existem versões de Fabric diferentes em perfis históricos; a versão exata do loader e a lista final dos mods deverão vir de uma versão oficial validada, nunca de uma suposição. `online-mode=false` no servidor não comprova identidade de nickname nem autoriza o launcher a ignorar a autenticação Atlas.

## Organização

```
apps/desktop/src/main       Electron: sistema operacional e IPC
apps/desktop/src/preload    Ponte mínima, sem APIs genéricas
apps/desktop/src/shared     Contratos sem dependências Electron
apps/desktop/src/renderer   React, estilos e apresentação
apps/desktop/test           Testes da fronteira de confiança
services/backend           API Java 21/Spring Boot independente
scripts                    Build e ambiente de desenvolvimento
docs                       Contratos e decisões
```

Fluxo atual: React → preload → IPC validado → configurações locais. Backend independente → health/status. Não há conexão automática entre desktop e backend nesta fase.

Fluxo futuro: renderer → serviços do processo principal → autenticação / atualização do pack / processo Minecraft. As três responsabilidades terão módulos separados quando implementadas. Backend controla releases e canais no MySQL; arquivos grandes ficam em object storage. Assinatura Ed25519 e SHA-256 serão validadas no processo principal, com instalação isolada, staging e rollback. SSE e consulta a cada cinco minutos apenas acionam nova verificação assinada; nunca concedem confiança ao conteúdo por si só.

Atualização do Electron é outro fluxo, com instaladores assinados e recuperação própria. Não deve reutilizar o mecanismo de substituição de mods. Prism, CurseForge e outros launchers continuam permitidos: política de compatibilidade pertence ao servidor.

## Dependências

Versões estáveis consultadas no registro npm e documentação oficial: Electron 45.0.0, React/React DOM 19.3.1, Vite 8.3.5, plugin React 6.1.2, TypeScript 7.0.2, esbuild 0.28.2 e tsx 4.23.15. Tipos React 19.3.0 e Node 24.10.1. Versões exatas e árvore em `package-lock.json`; Spring Boot 4.1.2, Java 21, Maven Wrapper existente reutilizado. Spring gerencia suas dependências pelo BOM.

Referências: [Electron](https://www.electronjs.org/docs/latest/tutorial/security), [Vite](https://vite.dev/guide/), [Spring Boot](https://docs.spring.io/spring-boot/system-requirements.html). Arte e logo reaproveitados de `atlas-web/public/atlas-hero.png` e `atlas-client/.../atlas-logo.png`.

## Pendências por fase

2. Login/conta/servidores/atualizações/erros com estados, acessibilidade e serviços tipados.
3. Manifesto assinado, comparação de arquivos, hashes, download retomável, locks, staging, rollback e proteção de dados pessoais; testes de cada falha.
4. MySQL + migrations, armazenamento, autorização administrativa, publicação atômica imutável e SSE/reconexão.
5. Registro Microsoft aprovado, proteção de tokens no cofre do SO, política offline publicada, Java/loader reais e lançamento seguro do modpack.
6. Instalador Windows, assinatura de código, atualização do aplicativo e testes Windows limpo.

## Interface 0.2.0

Páginas separadas em `renderer/pages`, ícones e barra de janela em `renderer/components`. Fluxo inicial de login não cria identidade: o usuário pode apenas conhecer a interface como visitante. Telas representam ausência de integração sem progresso, estatísticas ou contas inventadas. Configurações locais mantêm a validação original. A distribuição de prévia usa Electron Packager 20.3.0; o instalador, Authenticode e atualização segura do aplicativo permanecem na fase 6.
