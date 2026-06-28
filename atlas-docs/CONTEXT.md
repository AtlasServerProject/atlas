# Atlas Project Context

Version: 1.0

---

# Atlas

Sistema completo para um servidor profissional de Minecraft Cobblemon.

Este documento contém TODO o contexto arquitetural do projeto Atlas e deve ser utilizado por qualquer desenvolvedor ou IA antes de modificar o projeto.

Este documento possui prioridade sobre qualquer convenção padrão caso exista conflito.

---

# Objetivo do Projeto

O Atlas não é apenas um servidor de Minecraft.

O objetivo é criar uma plataforma completa composta por:

* Servidor Minecraft
* API REST
* Website
* Loja
* Painel Administrativo
* Sistema de Login
* Banco de Dados
* CLI própria
* Integração com Discord
* Economia persistente
* Sistema de VIP
* Sistema de Crates
* Sistema de GTS
* Sistema de Claims
* Sistema de Homes
* Sistema de Missões
* Sistema de Eventos

Toda a arquitetura foi projetada para crescer sem depender de plugins externos.

Sempre que possível devemos desenvolver módulos próprios.

---

# Filosofia do Projeto

O Atlas segue alguns princípios obrigatórios.

## 1. Não ser Pay To Win

Nunca vender dinheiro.

Nunca vender vantagem competitiva.

Nunca vender estatísticas.

Nunca vender itens exclusivos que desequilibrem o jogo.

A economia deve ser igual para todos.

---

## Monetização

A monetização ocorrerá através de:

### VIP

Benefícios de qualidade de vida.

Exemplos:

* mais homes
* mais claims
* mais kits
* mais cosmetics
* prioridade na fila
* chat colorido
* partículas
* comandos adicionais

Jamais bônus de dano ou dinheiro.

---

### Crates

Venda apenas de:

* Chaves
* Pokémon com texturas especiais
* Pokémon lendários
* Cosméticos
* Decorações
* Tags
* Emotes
* Partículas

Nunca vender dinheiro.

Nunca vender moedas.

Nunca vender vantagens econômicas.

---

## Economia

Toda moeda do servidor deve ser conquistada jogando.

Não existe compra direta de dinheiro.

Todo player inicia exatamente igual.

---

## Premium e Pirata

O Atlas permitirá entrada de:

* jogadores Premium
* jogadores Offline

Será implementado um sistema próprio de autenticação.

Premium entra automaticamente.

Offline deverá utilizar:

/register

/login

---

# Público alvo

Comunidade brasileira de Cobblemon.

Servidor inspirado em grandes redes como:

* Pixelmon Brasil
* Complex Gaming
* Hypixel

mas utilizando Cobblemon como base.

---

# Stack Tecnológica

Linguagem principal

Java 21

---

Minecraft

Fabric

Minecraft 1.21.1

---

Banco

PostgreSQL

---

Frontend

Angular

---

Backend Web

Spring Boot

---

CLI

Java

---

Website

Angular + Spring

---

IDE utilizada

VSCode

IntelliJ

---

Sistema Operacional

Ubuntu Server

VMWare

---

Controle de versão

Git

GitHub

Repositório Atlas

# Estrutura do Projeto

O Atlas foi projetado utilizando arquitetura modular.

Cada projeto possui uma responsabilidade única.

```
atlas/

├── atlas-api/
├── atlas-cli/
├── atlas-core/
├── atlas-docs/
├── atlas-web/
├── database/
├── infra/
├── minecraft/
└── README.md
```

---

# atlas-core

É o coração do servidor.

Tudo relacionado ao Minecraft está localizado aqui.

Responsabilidades:

* módulos
* economia
* ranks
* players
* crates
* vip
* claims
* homes
* pokémon
* eventos
* listeners
* comandos
* permissões
* cache

Nenhuma regra de negócio do Minecraft deve existir fora do atlas-core.

---

# atlas-api

Responsável pela API REST.

Comunica:

* Website
* Painel Administrativo
* Loja
* Discord
* CLI

Nunca acessa diretamente arquivos do Minecraft.

Toda comunicação ocorre através do banco.

---

# atlas-web

Frontend.

Construído utilizando Angular.

Responsável por:

* Loja
* Perfil
* Login
* Registro
* Painel do jogador
* Estatísticas
* Leaderboards
* Compra de VIP
* Compra de Crates

---

# atlas-cli

Ferramenta administrativa.

Objetivo:

Eliminar dependência do console do Minecraft.

Exemplos:

```
atlas-cli start

atlas-cli stop

atlas-cli restart

atlas-cli migrate

atlas-cli backup

atlas-cli restore

atlas-cli logs

atlas-cli status

atlas-cli rank

atlas-cli vip

atlas-cli player

atlas-cli economy
```

No futuro:

```
atlas-cli player ban

atlas-cli player kick

atlas-cli player info

atlas-cli economy give

atlas-cli crate give

atlas-cli rank set

atlas-cli maintenance
```

---

# database

Contém todas as migrations.

Nunca editar tabelas manualmente.

Toda alteração deve ocorrer através de migration.

Exemplo:

```
001_players.sql

002_economy.sql

003_auth.sql

...

021_ranks.sql

022_permissions.sql

...
```

---

# minecraft

Contém os arquivos reais do servidor.

```
fabric/

mods/

config/

world/

logs/

backups/
```

Nunca colocar código Java aqui.

---

# infra

Scripts de infraestrutura.

Exemplos:

```
install.sh

backup.sh

start.sh

update.sh
```

---

# atlas-docs

Documentação oficial.

Sempre manter atualizada.

Contém:

```
ARCHITECTURE.md

CONTEXT.md

DATABASE.md

SPRINTS.md

README.md

ROADMAP.md

CODING_STANDARD.md
```

---

# Arquitetura Geral

```
Minecraft

↓

Atlas Core

↓

Services

↓

Repositories

↓

PostgreSQL

↓

API

↓

Website

↓

Painel Administrativo
```

O banco de dados é o centro da arquitetura.

Todos os componentes conversam através dele.

---

# Organização de Pacotes

Todo módulo segue exatamente a mesma estrutura.

Exemplo:

```
economy/

cache/

commands/

listener/

model/

repository/

service/

EconomyModule.java
```

Outro exemplo:

```
rank/

cache/

commands/

listener/

model/

repository/

service/

formatter/

RankModule.java
```

Jamais misturar responsabilidades.

---

# Fluxo padrão

Todo sistema deverá seguir obrigatoriamente:

```
Command

↓

Service

↓

Repository

↓

Database
```

Nunca:

```
Command

↓

SQL
```

ou

```
Listener

↓

PreparedStatement
```

Toda regra de negócio pertence ao Service.

Toda comunicação com banco pertence ao Repository.

---

# Convenção de nomes

Model

Representa uma entidade.

Exemplo:

```
PlayerProfile

Rank

EconomyAccount
```

---

Repository

Responsável pelo SQL.

Nunca possuir lógica de negócio.

---

Service

Onde toda regra do servidor acontece.

É o cérebro do módulo.

---

Cache

Objetos carregados em memória.

Nunca utilizar SQL para consultar algo que já esteja em cache.

---

Listener

Eventos do Minecraft.

Jamais possuir lógica pesada.

Sempre chamar Services.

---

Command

Responsável apenas por:

* validar argumentos
* validar permissões
* chamar Services
* enviar mensagens

Nunca acessar banco diretamente.

# Database Architecture

Versão: 1.0

---

# Filosofia

O PostgreSQL é o centro da arquitetura do Atlas.

Toda informação persistente deve ser armazenada nele.

Nenhum módulo deve depender exclusivamente de arquivos JSON, YAML ou NBT para armazenar dados permanentes.

Arquivos locais podem existir apenas como cache ou configuração.

A fonte oficial de verdade sempre será o banco de dados.

---

# Tecnologias

Banco:

PostgreSQL

Driver JDBC

Java 21

Fabric

---

# Organização das Migrations

Todas as alterações estruturais do banco devem ocorrer através de migrations.

Nunca alterar tabelas manualmente em produção.

Estrutura:

001_core_players.sql

002_core_economy.sql

003_core_auth.sql

...

021_ranks.sql

022_permissions.sql

023_crates.sql

...

---

# Tabela players

Responsável por armazenar todos os jogadores do servidor.

Cada jogador possui apenas um registro.

Campos principais:

id

uuid

username

first_login

last_login

is_online

created_at

updated_at

---

UUID

O UUID é utilizado como identificador global.

Jamais utilizar username como chave primária.

O username poderá mudar futuramente.

O UUID nunca muda.

---

Relacionamentos

players

↓

economy_accounts

↓

player_ranks

↓

auth_accounts

↓

player_homes

↓

player_claims

↓

player_statistics

---

# economy_accounts

Cada jogador possui exatamente uma conta.

Campos:

player_id

balance

total_earned

total_spent

updated_at

---

Objetivo

Toda movimentação financeira do servidor utiliza esta tabela.

Exemplos:

Venda

Compra

Loja

GTS

Missões

Eventos

Crates

Recompensas

Nunca armazenar saldo em memória como fonte oficial.

O cache serve apenas para performance.

---

# auth_accounts

Responsável pelo sistema de autenticação.

Campos previstos:

player_id

password_hash

salt

premium

registered

last_ip

last_login

auto_login

---

Premium

Jogadores Premium não precisam utilizar login.

Offline deverão utilizar:

/register

/login

---

Hash

Nunca armazenar senhas em texto.

Utilizar BCrypt.

---

# ranks

Define todos os cargos do servidor.

Campos:

identifier

display_name

prefix

color

priority

staff

enabled

---

Exemplo

OWNER

ADMIN

MOD

SUP

VIP

PLAYER

---

Prioridade

Quanto maior a prioridade maior o cargo.

Exemplo

OWNER

100

ADMIN

90

MOD

70

PLAYER

0

---

# player_ranks

Relaciona jogadores com cargos.

O Atlas suporta múltiplos cargos por jogador.

Exemplo

Victor

↓

OWNER

VIP+

BETA_TESTER

EVENTO

Todos ativos simultaneamente.

---

O maior cargo define:

Prefixo

Cor

Tag

Nome no TAB

Chat

Nametag

---

As permissões são a união de todos os cargos.

---

# rank_permissions

Tabela responsável pelas permissões.

Exemplos

atlas.*

atlas.admin.*

atlas.economy.*

atlas.claim.*

atlas.crate.*

atlas.home.*

atlas.gts.*

atlas.player.fly

atlas.player.feed

*

---

Wildcard

O Atlas suporta:

Permissão exata

Wildcard parcial

Wildcard total

Exemplos

atlas.economy.addmoney

atlas.economy.*

atlas.*

*

---

# store_orders

Responsável pela loja.

Campos previstos

id

player_id

product

price

payment_method

status

gateway

transaction_id

created_at

---

Fluxo

Website

↓

API

↓

Gateway

↓

Pagamento aprovado

↓

Banco

↓

Atlas Core

↓

Entrega automática

---

# VIP

Tabela futura

vip_subscriptions

Campos

player_id

vip_type

started_at

expires_at

auto_renew

active

---

Crates

Tabela futura

crate_keys

Campos

player_id

crate

amount

---

Claim System

Tabela futura

claims

Campos

id

owner

world

x

z

size

flags

---

Homes

Tabela futura

homes

Campos

player_id

name

world

x

y

z

yaw

pitch

---

Pokémon

O Atlas nunca armazenará informações completas dos Pokémon.

Essas informações continuam sendo responsabilidade do Cobblemon.

O banco armazenará apenas dados necessários para integração.

Exemplo

Mercado

Eventos

Rankings

Histórico

Caixas

Recompensas

---

Backups

Backup automático diário.

Retenção

30 dias.

Backup manual disponível via:

atlas-cli backup

---

Princípios

Nunca apagar dados de jogadores.

Nunca reutilizar IDs.

Nunca utilizar DELETE quando um histórico puder ser preservado.

Preferir:

active

enabled

deleted_at

expires_at

Ao invés de remoção definitiva.

O Atlas prioriza rastreabilidade, auditoria e histórico de todas as ações relevantes.

# Sprint 1 — Core Foundation

Status: ✅ Concluída

---

# Objetivo

Criar toda a fundação do Atlas.

Nenhuma feature de gameplay seria implementada antes da existência de uma arquitetura sólida.

Toda decisão desta sprint foi voltada para escalabilidade.

---

# Tecnologias utilizadas

Java 21

Fabric API

Minecraft 1.21.1

Fabric Loom

PostgreSQL

JDBC

Gradle

---

# Objetivos da Sprint

Criar:

* Bootstrap
* Module Manager
* Sistema de módulos
* PostgreSQL
* Migrations
* Player System
* Economy
* Rank System
* Permission System

---

# Bootstrap

Foi criado:

AtlasBootstrap

Responsável por iniciar todos os módulos.

Fluxo:

Servidor inicia

↓

AtlasMod

↓

AtlasBootstrap.start()

↓

ModuleManager

↓

Registro dos módulos

↓

Inicialização

---

# ModuleManager

Criado para eliminar inicializações espalhadas.

Cada módulo possui:

enable()

disable()

Todos seguem a mesma interface.

Exemplo:

DatabaseModule

EconomyModule

PlayerModule

RankModule

---

# DatabaseModule

Primeiro módulo carregado.

Responsável por:

abrir conexão

validar PostgreSQL

manter conexão ativa

encerrar conexão corretamente

Todos os módulos dependem dele.

---

# PostgreSQL

Foi decidido utilizar PostgreSQL como banco oficial.

Motivos:

Escalabilidade

Performance

Confiabilidade

Suporte a transações

Boa integração com Spring

Boa integração com Java

---

# Sistema de Migrations

Toda alteração estrutural do banco ocorre através de migrations.

Nunca alterar tabelas manualmente.

Cada migration recebe um número sequencial.

Exemplo:

001_core_players

002_core_economy

021_ranks

---

# Player System

Criado durante esta sprint.

Classes implementadas:

PlayerProfile

PlayerRepository

PlayerCache

PlayerService

PlayerJoinListener

PlayerModule

---

Fluxo

Jogador entra

↓

JOIN Event

↓

PlayerJoinListener

↓

PlayerService

↓

PlayerRepository

↓

PostgreSQL

↓

Cache

---

Primeiro Login

Caso o jogador não exista:

Criar registro

Criar conta econômica

Atualizar login

Salvar cache

---

Login seguinte

Atualizar username

Atualizar último login

Atualizar online

Carregar cache

---

Logout

Atualizar banco

Remover cache

Atualizar status online

---

# Economy

Foi criada uma economia totalmente persistente.

Classes

EconomyRepository

EconomyService

EconomyModule

---

Fluxo

Comando

↓

EconomyService

↓

EconomyRepository

↓

Banco

---

Saldo

Implementado:

/saldo

Lê informações do cache.

Caso necessário consulta banco.

---

Depósito

Implementado:

deposit()

Atualiza cache.

Atualiza PostgreSQL.

---

Saque

Implementado:

withdraw()

Validação de saldo.

Persistência.

---

Set Balance

Implementado.

Atualiza banco imediatamente.

---

Objetivo

Nunca perder saldo em caso de queda do servidor.

---

# Rank System

Criado durante a Sprint.

Arquitetura

Rank

RankRepository

RankCache

RankService

RankModule

RankFormatter (em desenvolvimento)

---

Características

Múltiplos cargos por jogador.

Maior prioridade define:

prefixo

cor

nome

tag

TAB

Chat

Nametag

---

Permissões

As permissões são união de todos os cargos.

Exemplo

OWNER

VIP

BETA

↓

Todas permissões combinadas.

---

# Sistema de Permissões

Foi decidido abandonar completamente o sistema de OP do Minecraft.

Toda permissão pertence ao Atlas.

Criada classe:

Permission

Fluxo:

Command

↓

Permission

↓

RankService

↓

RankRepository

↓

Banco

---

Suporte

Permissão exata

Wildcard parcial

Wildcard global

Exemplos

atlas.economy.addmoney

atlas.economy.*

atlas.*

*

---

# Primeiro comando administrativo

Implementado:

/addmoney

Fluxo:

Comando

↓

Permission

↓

EconomyService

↓

Repository

↓

Banco

---

# Comandos implementados

/atlas

/saldo

/addmoney

---

# Cache

Todo jogador online permanece carregado.

Objetivo:

Reduzir consultas SQL.

Melhorar desempenho.

---

# Estrutura final da Sprint

AtlasBootstrap

↓

ModuleManager

↓

DatabaseModule

↓

RankModule

↓

EconomyModule

↓

PlayerModule

---

# Decisões Arquiteturais

Nenhum Command acessa SQL.

Nenhum Listener possui regra de negócio.

Nenhum Repository possui lógica.

Toda regra pertence aos Services.

---

# Problemas resolvidos

Compatibilidade Java 21.

Compatibilidade Fabric Loader.

Configuração Gradle.

Driver PostgreSQL.

Autenticação PostgreSQL.

Sistema de cache.

Persistência de saldo.

Permissões sem OP.

Wildcard de permissões.

---

# Estado da Sprint

Sprint 1 considerada concluída.

Toda infraestrutura do Atlas encontra-se operacional.

O projeto está preparado para crescimento modular sem necessidade de refatorações estruturais significativas.


# Sprint 2 — Visual Identity & Rank System

Status: 🚧 Em desenvolvimento

---

# Objetivo

A Sprint 2 tem como objetivo dar identidade visual ao servidor.

Até a Sprint 1 toda a infraestrutura ficou pronta.

Agora começaremos a desenvolver tudo o que o jogador realmente verá dentro do Minecraft.

Esta sprint é focada em:

* Sistema de cargos
* Tags
* TAB
* Chat
* Nametags
* Framework de comandos
* Evolução das permissões

---

# Estado Atual

Ao iniciar esta Sprint o Atlas já possui:

✔ Bootstrap

✔ PostgreSQL

✔ Cache

✔ Economy

✔ Player System

✔ Rank System

✔ Permission System

✔ Commands

Todo o restante será construído sobre essa base.

---

# Rank System

O sistema de cargos foi projetado para ser totalmente independente do sistema de OP do Minecraft.

Todo o gerenciamento ocorre pelo PostgreSQL.

Estrutura:

Ranks

↓

Permissions

↓

PlayerRanks

↓

RankService

↓

Permission

↓

Commands

---

# Filosofia

Nunca depender de:

Minecraft OP

LuckPerms

Permission Plugins

Toda autorização deve acontecer dentro do Atlas.

---

# Sistema de Cargos

Atualmente existem os seguintes cargos planejados:

OWNER

DEV

ADMIN

MOD

SUP

HELPER

YOUTUBER

CONTENT

VIP++

VIP+

VIP

PLAYER

Cada cargo possui:

Prefixo

Cor

Prioridade

Permissões

Status Staff

Enabled

---

# Prioridade

Quanto maior a prioridade maior o cargo.

Exemplo:

OWNER

↓

DEV

↓

ADMIN

↓

MOD

↓

SUP

↓

PLAYER

O maior cargo define:

Prefixo

Cor

Tag

TAB

Chat

Nametag

---

# Múltiplos Cargos

Um jogador pode possuir vários cargos.

Exemplo:

Victor

↓

OWNER

VIP++

BETA_TESTER

NATAL2026

As permissões serão a união de todos os cargos.

---

# Wildcards

O sistema suporta:

Permissão específica

atlas.home.set

Permissão parcial

atlas.home.*

Permissão de módulo

atlas.*

Permissão global

*

---

# Permission API

Todos os comandos devem utilizar:

Permission.check()

Jamais utilizar:

source.hasPermission()

OP

LuckPerms

---

# Rank Formatter

Status

🚧 Em desenvolvimento

Responsável por transformar:

Rank

↓

Prefixo

↓

Cor

↓

Component

Exemplo

[ADM] Victor

[VIP] João

[DEV] Carlos

---

# TAB

Primeira implementação visual.

Objetivo:

Mostrar:

[ADM] Victor

Ao apertar TAB.

Sem alterar o nome verdadeiro do jogador.

---

# Chat

Planejado

Formato:

[ADM] Victor

Olá pessoal!

Suporte a:

Hover

Click

MiniMessage

Hex Colors

Gradientes

---

# Nametag

Planejado

Mostrar acima da cabeça:

[ADM]

Victor

Atualização automática.

---

# Atualização em Tempo Real

Quando um administrador alterar um cargo:

/rank set

ou

painel administrativo

ou

site

O jogador não deverá reconectar.

O RankService deverá atualizar:

TAB

Chat

Nametag

Permissões

Instantaneamente.

---

# Framework de Comandos

Durante esta Sprint iniciaremos um novo framework.

Hoje:

AtlasCommand

BalanceCommand

AddMoneyCommand

No futuro:

EconomyCommand

↓

saldo

pay

addmoney

setmoney

removemoney

RankCommand

↓

set

remove

info

list

CrateCommand

↓

give

open

reload

VipCommand

↓

give

remove

reload

HomeCommand

ClaimCommand

PlayerCommand

AdminCommand

Isso reduzirá drasticamente o número de classes.

---

# Economy

Próximos comandos

/pay

/removemoney

/setmoney

/topmoney

/baltop

/history

Todas utilizando EconomyService.

---

# Rank Administration

Será criado:

/rank

Subcomandos:

set

remove

list

info

reload

permission add

permission remove

---

# CLI

O atlas-cli também passará a controlar cargos.

Exemplos:

atlas-cli rank set Victor admin

atlas-cli rank remove Victor vip

atlas-cli player info Victor

atlas-cli economy give Victor 100

---

# Estado Atual do Código

Implementado:

✔ RankRepository

✔ RankCache

✔ RankService

✔ RankModule

✔ Permission

✔ Wildcards

Em desenvolvimento:

RankFormatter

TAB

Chat Formatter

Nametag Formatter

---

# Próximo Objetivo

Concluir completamente o sistema visual de cargos.

Ao final da Sprint 2 o servidor deverá apresentar:

✔ Prefixo no TAB

✔ Prefixo no Chat

✔ Prefixo acima da cabeça

✔ Atualização automática

✔ Framework de comandos iniciado

A Sprint 2 termina quando a identidade visual completa do servidor estiver operacional.
