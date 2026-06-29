# Sprints do Atlas

## Sprint 1 — Core Foundation

Status: ✅ Concluída

- [x] PostgreSQL
- [x] Migrations
- [x] Module Manager
- [x] Player System
- [x] Economy
- [x] Rank
- [x] Permission
- [x] Cache

---

## Sprint 2 — Visual Identity & Ranks

Status: ✅ Concluída

- [x] Rank Formatter
- [x] Tags visuais de cargos
- [x] Chat Formatter
- [x] Nametag
- [x] TAB
- [x] Sincronização de ranks em tempo real
- [x] Administração completa por `/rank`
- [x] Integração de permissões vanilla sem OP
- [x] Feedback privado de comandos administrativos

Versão final: `v1.4.0`

---

## Sprint 3 — Authentication

Status: 🚧 Próxima

### Fundação

- [x] Migration `auth_accounts`
- [x] Migration `player_sessions`
- [x] AuthModule
- [x] AuthRepository
- [x] AuthService
- [x] AuthSessionCache

### Registro e login

- [x] `/register <senha> <confirmacao>`
- [x] Hash seguro de senha com BCrypt
- [x] `/login <senha>`
- [ ] `/logout`
- [x] Sessão persistente por jogador
- [ ] Expiração e encerramento de sessões

### Proteção

- [ ] Bloquear movimentação antes do login
- [ ] Bloquear chat e comandos antes do login
- [ ] Bloquear inventário e interações antes do login
- [ ] Bloquear dano antes do login
- [ ] Limitar tentativas e aplicar cooldown
- [ ] Ocultar mensagens sensíveis dos logs

### Premium

- [ ] Identificar contas Premium
- [ ] Login automático para Premium
- [ ] Manter `/register` e `/login` para jogadores Offline

### Entrega

- [ ] Testes de registro, login e reconexão
- [ ] Documentação da versão
- [ ] Build, implantação e validação em produção

---

## Sprint 4 — Homes

Status: ⏳ Planejada

- [x] Migration `homes`
- [ ] HomeModule
- [ ] HomeRepository
- [ ] HomeService
- [ ] `/home`
- [ ] `/sethome`
- [ ] `/delhome`
- [ ] Limites por cargo e VIP
- [ ] Teleporte seguro
- [ ] Cooldown de teleporte

---

## Backlog

- Claims
- VIP
- Crates
- GTS
- Missões
- Eventos
- API REST
- Website e loja
- CLI administrativa
- Integração com Discord
