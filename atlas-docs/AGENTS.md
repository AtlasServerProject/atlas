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