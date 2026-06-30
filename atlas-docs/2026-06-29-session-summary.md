# Resumo técnico da sessão — 2026-06-29

Este documento substitui o primeiro relato da sessão por uma versão auditada contra o código, o banco, os artefatos e os logs de produção.

## O que foi mantido

- Ícone do servidor corrigido em produção.
- O acesso administrativo iniciado via RCON foi posteriormente substituído pelo console próprio Atlas.
- Fundação do pré-login Premium mantida: resolvedor assíncrono, cache, fail-closed e integração com o desafio vanilla.

## Problemas encontrados na implementação anterior

- O arquivo implantado se chamava `atlas-core-1.8.0.jar`, mas declarava internamente a versão `1.7.0`.
- A conta Premium era marcada apenas em memória; não era persistida nem autenticada automaticamente.
- Quando já existia `auth_account`, a marca Premium verificada podia ser ignorada.
- Não existia migração do UUID Offline para o UUID oficial.
- `VFSomente` ficou duplicado no banco: o perfil Offline concentrava cargo e saldo, enquanto o perfil oficial concentrava a autenticação.
- Não existia migração ou backup dos arquivos vanilla e Cobblemon vinculados ao UUID.
- O changelog afirmava preservação de UUID sem que isso estivesse implementado.
- `atlas-cli console` passava a senha na linha de comando e repetia uma entrada na ajuda.
- O script `infra/scripts/backup.sh` ainda é um placeholder e não cria backups reais.
- O RCON escutava em todas as interfaces na porta `25575` antes da substituição pelo socket Unix.

## Reformulação aplicada

- Versão Premium entregue como `1.8.0`; console próprio entregue como `1.9.0`.
- Nome Premium exige prova oficial da sessão Minecraft antes de entrar.
- Conta Premium é persistida como verificada e recebe login automático.
- Offline continua com `/register` e `/login`.
- Identidades duplicadas são unidas transacionalmente após a verificação Premium.
- Ranks, economia, sessões e referências dos demais módulos são transferidos ao UUID oficial.
- Arquivos do mundo são migrados uma única vez, com backup do destino existente.
- `atlas-cli console` e `atlas-cli exec` passaram a usar o socket Unix do Atlas.
- RCON desabilitado, senha removida e porta `25575` fechada.
- Documentação e Sprint 3 foram atualizadas conforme o estado real.

## Backups reais criados

```text
/opt/atlas/server/backups/atlas-db-2026-06-29-v1.8.0-predeploy.dump
/opt/atlas/server/backups/atlas-world-2026-06-29-v1.8.0-predeploy.tar.gz
/opt/atlas/server/backups/mod-versions/atlas-core-1.7.0-pre-premium.jar
```

## Estado atual

- Serviço `atlas`: ativo.
- Atlas Core carregado: `1.9.0`.
- Build e startup: validados.
- Artefato ativo: SHA-256 `cca656201df8b7414e9c83ffcf9e344ab182719db5d38a5f01ffbc41365d554d`.
- Teste pendente: reconectar `VFSomente` com a conta original e validar login automático, cargo, saldo e dados do jogador.
