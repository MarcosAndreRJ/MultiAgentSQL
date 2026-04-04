## Plano: Agent Bindings (Passo 3.1)

Objetivo: preparar contratos (schemas Pydantic) e serviços de leitura seguros para
dar suporte à governança dos bots (Agent ⇄ LLM Provider/Model e Agent ⇄ Target DB),
sem ativar conexão real com target_db nem alterar infra existente.

Arquivos criados:

- `app/schemas/agent_bindings.py` — Pydantic DTOs para create/update/read de bindings
- `app/services/platform/agent_bindings_service.py` — serviços de leitura seguros (somente leitura)
- `app/utils/secrets.py` — helpers para mascaramento e serializacao segura
- `app/api/routes_agent_bindings.py` — rascunho de rotas (NAO registrado em main.py)
- `docs/agent-bindings-plan.md` — este documento

Comportamento e restricoes:
- Nao altera models SQLAlchemy existentes.
- Nao cria migrations.
- Nao implementa conexao real com target_db.
- Nao registra rotas no app principal para evitar conflito.
- Saidas nunca expõem `password`; em vez disso expõem `has_password`.

Garantias e decisões importantes (Etapa 6):

- Apenas 1 binding default por agent: o serviço que cria/atualiza bindings garante que
  quando um binding é marcado como `is_default=True`, quaisquer outros bindings do
  mesmo `agent_id` terão `is_default` limpo (update). Essa garantia é aplicada na
  camada de aplicação (service). Em ambientes que exigem enforcement no nível de
  banco, recomenda-se adicionar um mecanismo adicional (trigger/constraint) específico
  para o engine de banco usado.

- Coerência entre `fallback_provider_id` e `fallback_model_id`: a validação server-side
  exige que ambos sejam informados juntos e que o `fallback_model` pertença ao
  `fallback_provider`. Caso contrário, a API rejeitará a operação com erros claros.

- Comportamento sem fallback em YAML por enquanto: a resolução de binding (`resolve_agent_llm_binding`)
  atualmente utiliza apenas o `platform_db`. Se nenhum binding for encontrado no DB,
  o resolvedor retorna `binding: null`, `is_valid: false` e `validation_errors` com
  uma mensagem "no binding found". A estratégia de fallback para os yaml bootstrap
  será implementada separadamente durante a migração; por enquanto o dashboard deve
  usar as APIs para criar/atualizar rows no platform_db para que o agente tenha
  um binding oficial.

O que falta para o Passo 3.2:
- Endpoints seguros de CRUD para bindings (create/update/delete) com validações e auditoria.
- Implementacao de factory para `TargetDatabaseConnection` por `db_type`.
- Execucao controlada de queries e introspecao de schema no `target_db` (com limites e safeties).

Notas de integracao:
- A camada de leitura usa `agent_registry` para lista de agentes; isso evita depender de tabelas de agentes no DB.
- Os serviços cuidam do caso de `platform_db` offline retornando respostas controladas.
