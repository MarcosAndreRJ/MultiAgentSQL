# MultiAgent SQL

Sistema de múltiplos agentes independentes para operar bancos MySQL usando LLMs locais via **Ollama**.

## Visão Geral

MultiAgent SQL é um runtime persistente com agentes especializados. Cada agente tem uma identidade, um banco de dados vinculado (opcional) e um conjunto de skills. Usuários conversam diretamente com o agente desejado — sem delegação automática entre agentes.

```
┌─────────────────────────────────────────────────────┐
│                  MultiAgent SQL                      │
│                                                      │
│  ┌───────────────┐    ┌──────────────────────────┐  │
│  │   Web UI      │    │       FastAPI API         │  │
│  │  (Chat)       │────│   /api/agents /api/chat   │  │
│  └───────────────┘    └──────────────────────────┘  │
│                                  │                   │
│                         ┌────────▼─────────┐         │
│  ┌──────────────────────┤   Agent Router   ├───────┐ │
│  │                      └──────────────────┘       │ │
│  │                                                  │ │
│  ▼ Principal Agent      ▼ MySQL Specialist Agent(s) │ │
│  [llm only]             [plan → tools → guard → DB] │ │
└─────────────────────────────────────────────────────┘
```

## Tipos de Agente

| Tipo | Descrição |
|------|-----------|
| `principal` | Generalista. Responde via LLM sem acessar banco. |
| `mysql-specialist` | Vinculado a um banco MySQL. Executa SQL, inspeciona schema, gera mock data. |

## Estrutura do Projeto

```
multiagent-sql/
├── app/
│   ├── api/          # Rotas FastAPI (agents, chat, execution, pending, skills)
│   ├── agents/       # Agentes (base, principal, database) + prompt_builder + skill_loader
│   ├── core/         # settings, logger, sql_classifier, guard_engine, pending_actions,
│   │                 # agent_registry, session_store
│   ├── schemas/      # Pydantic schemas (agent, chat, execution, guard, pending, skill)
│   ├── services/     # ollama_client, chat_service, agent_service, execution_service, pending_service
│   ├── tools/        # db_connection_manager, db_execute, db_introspection, db_schema_cache,
│   │                 # db_mockdata, sql_formatter, sql_estimator
│   ├── web/          # Interface web (templates/, static/)
│   └── main.py       # Entry point FastAPI
├── cli/
│   └── main.py       # CLI com Typer
├── config/
│   ├── agents/       # YAMLs de configuração de agentes
│   ├── prompts/      # Arquivos de prompt base .md
│   └── skills/       # Arquivos de skills .md
├── tests/            # Testes unitários
├── logs/             # Logs de runtime
├── requirements.txt
└── .env.example
```

## Setup

### 1. Pré-requisitos

- Python 3.12+
- [Ollama](https://ollama.ai) instalado e rodando localmente
- MySQL acessível (para agentes especialistas)

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com suas configurações
```

### 4. Configurar seu agente MySQL

Crie `config/agents/meu-banco.yaml`:

```yaml
id: meu-banco
name: Agente meu-banco
description: Especialista no banco meu_banco_dev
type: mysql-specialist
model: llama3.1:8b
prompt_file: mysql-specialist.md
skills:
  - mysql-defaults
  - ddl-rules

database:
  host: localhost
  port: 3306
  name: meu_banco_dev
  user: root
  password: ""

permissions:
  can_read_db: true
  can_write_db: true
  can_ddl: true
  can_execute: true
  protected_tables: []

guards:
  require_confirmation_for:
    - DELETE
    - DROP
    - TRUNCATE
    - UPDATE_WITHOUT_WHERE
    - ALTER_DESTRUCTIVE
  auto_approve:
    - SELECT
    - SHOW
    - DESCRIBE
    - EXPLAIN
```

### 5. Baixar um modelo Ollama

```bash
ollama pull llama3.1:8b
# ou
ollama pull qwen2.5-coder:7b
```

## Rodando

### API + Web UI

```bash
python -m app.main
# ou
uvicorn app.main:app --reload --port 8000
```

Acesse: http://localhost:8000

### CLI

```bash
# Listar agentes
python -m cli.main list-agents

# Chat interativo
python -m cli.main chat meu-banco

# Enviar mensagem única
python -m cli.main send meu-banco "Liste as tabelas do banco"

# Testar conexão
python -m cli.main test-connection meu-banco

# Listar pending actions
python -m cli.main list-pending --agent meu-banco

# Confirmar pending action
python -m cli.main confirm pa_abc123 --agent meu-banco
```

### Testes

```bash
pytest tests/ -v
```

## Agent Loop (MySQL Specialist)

```
mensagem do usuário
    ↓
construir prompt (base + skills + contexto + histórico)
    ↓
gerar plano LLM (intent, needs_tools, sql, tools, risk_hint)
    ↓
executar tools indicadas (db_introspect, db_execute, db_mockdata)
    ↓
guard avalia SQL
    ├── bloqueado → resposta de erro
    ├── requer confirmação → cria pending action → aguarda usuário
    └── aprovado → executa no banco → retorna resultado real
    ↓
formatar resposta estruturada
```

## Formato de Resposta

Respostas do agente seguem um formato estruturado com blocos:

```
[RESUMO]
Objetivo da operação

[SQL]
```sql
SELECT * FROM users WHERE active = 1
```

[RESULTADO]
id | name  | email
---|-------|------
1  | Ana   | ana@...
2  | Pedro | pedro@...

[STATUS]
Executado com sucesso (12.3ms)
```

Para operações de risco:

```
[RISCO]
HIGH | DELETE sem WHERE afeta TODOS os registros

[AÇÃO NECESSÁRIA]
Confirme para executar ou cancele.

[ID]
pa_abc123def456

[PRÓXIMO PASSO]
Responda 'confirmar pa_abc123def456' ou 'cancelar pa_abc123def456'
```

## Pending Actions

Operações de alto risco geram **pending actions** que aguardam confirmação:

| Operação | Comportamento padrão |
|----------|---------------------|
| DELETE | Exige confirmação |
| DROP | Exige confirmação |
| TRUNCATE | Exige confirmação |
| UPDATE sem WHERE | Exige confirmação |
| ALTER destrutivo | Exige confirmação |
| SELECT | Auto-aprovado |
| SHOW/DESCRIBE | Auto-aprovado |

TTL padrão: 30 minutos. Após expirar, a operação deve ser re-solicitada.

## Skills

Skills são arquivos `.md` em `config/skills/` que fornecem regras e padrões para guidar o agente. Não são código executável — são conhecimento estruturado incluído no prompt.

```
config/skills/
├── mysql-defaults.md    # Regras gerais MySQL
├── ddl-rules.md         # Boas práticas DDL
└── mockdata-defaults.md # Estratégias para mock data
```

Para adicionar uma skill a um agente em runtime (sem reiniciar):
```
POST /api/agents/{agent_id}/skills?skill_id=nome-da-skill
```

## Anti-Delusion

O sistema implementa regras para evitar alucinações:

- **Tool-first**: Agentes devem consultar o banco antes de afirmar sobre schema
- **Guard**: Backend valida e controla execução — LLM não executa diretamente
- **Resposta real**: Resultados vêm sempre de execução real no banco
- **Sem invenção**: Agente não deve inventar tabelas, colunas ou dados
- **Validação LLM**: Resposta JSON do LLM é validada e normalizada antes do uso

## Limitações Conhecidas

- Memória em memória (RAM): sem persistência entre reinicializações
- LLMs menores podem não seguir o formato JSON corretamente (fallback implementado)
- Sem autenticação: sistema não tem login/auth (para uso local/interno)
- Sem suporte a múltiplos bancos por agente

## Próximos Passos

- [ ] Persistência de sessões e pending actions (SQLite/Redis)
- [ ] Autenticação básica
- [ ] Suporte a PostgreSQL
- [ ] Histórico de conversas persistente
- [ ] Exportação de histórico de execuções
- [ ] Interface de administração de skills via UI
