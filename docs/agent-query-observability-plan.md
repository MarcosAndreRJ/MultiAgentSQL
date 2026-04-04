## Etapa 7.2 + 9.2: Execução real por binding e observabilidade

Este documento descreve a integração operacional Agent -> Database Binding -> Query,
com observabilidade persistida no `platform_db`.

### 1) Arquitetura de execução (7.2)

- Fonte de verdade de conexão: `agent_database_bindings_v2` + `database_connections`.
- Resolução do binding: `resolve_agent_database_binding(db, agent_id, database_connection_id=None)`
  - considera apenas bindings `is_active = true`
  - prioriza `is_default = true`
  - fallback para o primeiro ativo
  - exige `database_connections.is_active = true`
  - retorna erro controlado quando não houver binding válido
- O executor SQL **não** aceita credenciais do frontend.
- O endpoint `POST /api/agents/{agent_id}/query` recebe apenas `query`.

### 2) Segurança SQL

- Validação estrutural com `sqlglot`.
- Permitido somente `SELECT`.
- Bloqueio explícito de DDL/DML (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc).
- Bloqueio de múltiplos statements (`;`).
- `LIMIT` forçado em no máximo 100 linhas.
- `access_mode` respeitado no binding:
  - `readonly`: apenas leitura
  - `readwrite`: ainda sem escrita nesta etapa (bloqueio mantido)

### 3) Logs e correlação (9.2)

- Nova tabela: `agent_execution_logs`
  - guarda execução real por agente com `execution_id`, query sanitizada, status e latência.
- Nova tabela: `provider_execution_logs`
  - guarda latência/falha de chamadas operacionais de provider (`test_connection`, `sync_models`).
- `health_check_logs` ganhou campo opcional `execution_id` para correlação.
- Todas as persistências evitam segredos:
  - query sanitizada e truncada
  - erro sanitizado
  - nunca salva senha/connection string completa

### 4) APIs de observabilidade

- `GET /api/observability/agents`
  - métricas agregadas por agente:
    - total_executions
    - success_rate
    - avg_latency_ms
    - last_execution_at
- `GET /api/observability/agents/{agent_id}/logs?page=&page_size=`
  - logs detalhados com paginação.

### 5) Compatibilidade e limites desta etapa

- Não há alteração de UI.
- Não há habilitação de escrita SQL.
- Não há dependência de YAML no novo endpoint de execução por agente.
- O executor legado permanece disponível; a integração foi incremental.
