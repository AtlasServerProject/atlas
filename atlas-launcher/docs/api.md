# API — contrato da fase 1

Base local: `http://127.0.0.1:8091`. Não publicada na internet. Não altera a API do site.

| Método/caminho             | Estado                              | Autorização           |
| -------------------------- | ----------------------------------- | --------------------- |
| GET /actuator/health       | Implementado: `{"status":"UP"}`     | Público, sem detalhes |
| GET /api/launcher/status   | Implementado: capacidade do serviço | Público               |
| Qualquer outra rota/método | Negado por padrão                   | Não disponível        |

Status retorna `schemaVersion:1`, `service:"atlas-launcher-api"`, `version:"0.1.0"`, `phase:"foundation"`, `releasesAvailable:false`, `authenticationAvailable:false`, `eventsAvailable:false`. Health indica processo saudável, não instalação pronta, banco conectado ou servidor Minecraft disponível.

## Contratos planejados, NÃO implementados

- `GET /api/launcher/latest?channel=stable`: referência imutável do manifesto, versão mais recente e mínima compatível separadas.
- `GET /api/launcher/versions/{version}`: metadados e manifesto assinado.
- `GET /api/launcher/changelog`: histórico paginado.
- `GET /api/launcher/events`: SSE `release-published`, ID persistente, heartbeat, reconexão e Last-Event-ID; evento contém referência, não código.
- POST releases/publish/rollback: identidade administrativa autenticada, papel de publicador, auditoria, idempotência e transação para troca do canal. Sem autenticação não haverá publicação.

Na fase 4 serão definidos schemas de request/response e erros para esses endpoints e migrations MySQL das releases, arquivos, canais, publicações, rollback e auditoria. Não há endpoints simulados de autenticação, hashes inventados ou conta administrativa padrão.
