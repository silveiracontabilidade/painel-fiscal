## Audit log

### O que faz
- Grava ações `create`, `update` e `delete` para os modelos configurados em `AUDITLOG_INCLUDE_MODELS`.
- Registra diffs em JSON, usuário (se autenticado), caminho HTTP, método e IP.

### Configuração
- `settings.INSTALLED_APPS` inclui `auditlog`.
- Middleware `auditlog.middleware.CurrentRequestMiddleware` já registrado.
- Modelos monitorados padrão: `nfse.ReinfNFS`, `nfse.ImportJob`, `nfse.ImportJobFile`. Ajuste via `AUDITLOG_INCLUDE_MODELS`.
- Campos ignorados em diffs: `AUDITLOG_EXCLUDE_FIELDS` (default `['updated_at']`).

### API de consulta
- Endpoint GET `/api/audit/logs/`
- Filtros via querystring: `app`, `model`, `object_pk`, `action`, `actor`, `from`, `to` (datas em ISO, ex.: `2025-01-15T12:00:00Z`).

### Exemplos
- `GET /api/audit/logs/?app=nfse&model=ReinfNFS&object_pk=123`
- `GET /api/audit/logs/?actor=5&from=2025-01-01T00:00:00Z&to=2025-01-31T23:59:59Z`
