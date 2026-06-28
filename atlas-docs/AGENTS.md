# AGENTS

Toda feature deve seguir:

Command
↓

Service
↓

Repository
↓

Database

Nunca acessar SQL diretamente em Commands.

Sempre criar migrations.

Sempre utilizar cache quando possível.

Nunca criar lógica de negócio em Listeners.

## Release do atlas-core

Toda atualização do `atlas-core` só é considerada entregue depois de:

1. Atualizar a versão e registrar as mudanças em `atlas-docs/versions/`.
2. Executar `./gradlew build`.
3. Preservar uma cópia do JAR atualmente instalado.
4. Substituir o JAR antigo em `/opt/atlas/server/fabric/mods/` pelo novo.
5. Garantir que exista apenas um JAR do `atlas-core` na pasta de mods.
6. Reiniciar o serviço `atlas`.
7. Confirmar que o serviço está ativo e revisar os logs de inicialização.

Nunca deixar uma atualização apenas compilada no workspace.

Nunca armazenar senhas na documentação, em scripts ou no código-fonte.
