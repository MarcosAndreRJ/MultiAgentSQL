
# Architecture - MultiAgent SQL (Ollama + MySQL Executors)

## Visao Geral

O MultiAgent SQL e uma plataforma local em Python, orientada a eventos, composta por agentes independentes capazes de operar bancos MySQL de forma assistida, segura e executavel.

Diretriz principal:

"O sistema deve operar como um runtime persistente orientado a eventos, com agentes independentes, utilizando Web Chat como interface principal (e opcionalmente Telegram), mantendo contexto de conversa e permitindo execucao controlada de operacoes reais em banco de dados."

Cada agente funciona como uma unidade autonoma:

- possui prompt proprio
- possui skills associadas
- pode possuir conexao com database
- opera de forma independente dos demais

---

## Objetivo Arquitetural

Construir um sistema que permita:

- operacao real de banco via agentes
- execucao controlada (nunca direta pelo LLM)
- protecao contra acoes criticas
- uso de models locais (Ollama)
- extensao via skills
- controle total pelo backend

---

## Principios Arquiteturais

### 1. Agentes independentes

- nao existe orquestrador entre agentes
- cada agente responde diretamente ao usuario
- cada agente tem contexto proprio

---

### 2. Backend como autoridade

- o LLM nao executa nada diretamente
- toda execucao passa por services Python
- validacao sempre ocorre no backend

---

### 3. Tool-first architecture

- agentes dependem de tools reais
- nenhuma resposta baseada em suposicao quando dados existem
- introspecao obrigatoria quando necessario

---

### 4. Guard obrigatório

- toda acao critica passa por guard
- nenhuma execucao destrutiva direta
- confirmacao humana obrigatoria quando aplicavel

---

### 5. Prompt + Skills

O comportamento do agente e definido por:

- prompt base (identidade)
- skills (conhecimento estruturado)

---

### 6. Runtime persistente

- sistema sobe uma vez
- permanece ativo
- processa multiplas mensagens
- mantem contexto por sessao

---

## Stack

- Python 3.12+
- FastAPI
- Uvicorn
- MySQL (mysql-connector ou SQLAlchemy)
- Ollama (HTTP local)
- HTML + CSS + JS leve (UI)
- Typer (CLI opcional)

---

## Estrutura de Pastas

```text
multiagent-sql/
  app/
    main.py

    api/
      routes_agents.py
      routes_chat.py
      routes_execution.py
      routes_skills.py

    core/
      settings.py
      agent_registry.py
      session_store.py
      guard_engine.py
      sql_classifier.py
      pending_actions.py
      logger.py

    agents/
      base_agent.py
      principal_agent.py
      database_agent.py
      prompt_builder.py
      skill_loader.py

    tools/
      db_connection_manager.py
      db_introspection.py
      db_read.py
      db_write.py
      db_ddl.py
      db_mockdata.py
      db_safety.py
      sql_formatter.py
      sql_estimator.py

    services/
      ollama_client.py
      chat_service.py
      execution_service.py
      guard_service.py
      agent_service.py

    schemas/
      agent.py
      chat.py
      execution.py
      guard.py
      skill.py

    web/
      static/
      templates/

  cli/
    main.py

  config/
    agents/
      principal.yaml
      mysql_dev.yaml

    skills/
      mysql-playbook.md
      ddl-rules.md

  logs/
  tests/
````

---

## Componentes Principais

### 1. AppRuntime / Bootstrap

Responsavel por:

* carregar configs
* iniciar FastAPI
* inicializar agentes
* inicializar conexoes
* manter runtime ativo

---

### 2. Agent Registry

Responsavel por:

* carregar agentes via config
* manter lista de agentes
* resolver agente por ID
* associar:

  * prompt
  * skills
  * database

---

### 3. Agent Layer

#### BaseAgent

* estrutura comum
* contexto
* interface de execucao

---

#### PrincipalAgent

* nao possui database
* apenas raciocinio
* nao executa tools de banco

---

#### DatabaseAgent

* possui conexao MySQL
* pode executar operacoes reais
* utiliza tools obrigatoriamente

---

### 4. Skill Loader

Responsavel por:

* carregar arquivos `.md`
* concatenar skills ao prompt
* manter estrutura organizada

Fluxo:

```text
Prompt base
 + Skills atribuídas
 = Prompt final do agente
```

---

### 5. Chat Service

Responsavel por:

* receber mensagem
* identificar agente
* montar contexto
* chamar LLM
* interpretar resposta estruturada

---

### 6. Ollama Client

Responsavel por:

* enviar prompt
* receber resposta
* tratar timeout/erro
* padronizar retorno

---

### 7. Tool Layer

Ferramentas reais do sistema.

Categorias:

#### Introspection

* schema
* tabelas
* colunas
* DDL

#### Read

* SELECT
* EXPLAIN

#### Write

* INSERT / UPDATE / DELETE

#### DDL

* CREATE / ALTER / DROP

#### Mock Data

* geracao

---

### 8. Execution Service

Responsavel por:

* executar SQL
* validar SQL
* capturar erro
* retornar resultado real
* logar execucao

---

### 9. Guard Engine

Responsavel por:

* classificar SQL
* identificar risco
* bloquear execucao direta
* gerar pendencia
* solicitar confirmacao

---

### 10. Pending Actions

Armazena operacoes aguardando confirmacao.

Estrutura:

```json
{
  "id": "...",
  "agent_id": "...",
  "database": "...",
  "sql": "...",
  "risk_level": "low|medium|high",
  "status": "pending|confirmed|expired",
  "created_at": "...",
  "expires_at": "..."
}
```

---

### 11. Session Store

Memoria por agente e conversa.

Armazena:

* historico recente
* contexto
* tabelas acessadas
* queries recentes
* pendencias

---

### 12. API Layer (FastAPI)

Responsavel por:

* endpoints REST
* integracao com UI
* controle de fluxo

---

### 13. Web Interface

Responsavel por:

* selecao de agente
* chat
* visualizacao de SQL
* confirmacao de acoes
* gestao de skills

---

## Fluxo Principal

```text
Usuario (Web UI)
  ↓
API (routes_chat)
  ↓
ChatService
  ↓
Agent (prompt + skills)
  ↓
LLM (Ollama)
  ↓
Resposta estruturada
  ↓
Guard Engine (se necessario)
  ↓
Execution Service
  ↓
Banco MySQL
  ↓
Resultado real
  ↓
Resposta ao usuario
```

---

## Fluxo com Guard

```text
Agente gera SQL
  ↓
Guard Engine classifica
  ↓
Se risco alto:
    cria pending action
    solicita confirmacao
  ↓
Usuario confirma
  ↓
Execution Service executa
```

---

## Modelo de Execucao

### Startup

1. iniciar app
2. carregar agentes
3. carregar skills
4. iniciar API
5. UI pronta

---

### Runtime

* cada mensagem = 1 ciclo
* sistema permanece ativo
* memoria mantida

---

## Regras Criticas

### 1. Execucao nunca direta

* LLM nao executa SQL
* backend executa

---

### 2. Anti-delirio

* sem inventar schema
* uso obrigatorio de tools quando necessario

---

### 3. Confirmacao obrigatoria

* DELETE / DROP / TRUNCATE
* ALTER critico
* bulk operations

---

### 4. Logging

* todas execucoes registradas

---

## Concorrencia

* 1 fluxo por conversa
* evitar conflito de execucao simultanea

---

## Edge Cases

* conexao falha
* SQL invalido
* timeout Ollama
* confirmacao expirada
* schema inconsistente

---

## Limites

O sistema nao deve:

* permitir execucao sem controle
* depender de LLM para logica critica
* executar comandos fora do banco
* permitir multi-agent orchestration automatica

---

## Resumo

A arquitetura do MultiAgent SQL e:

* modular
* segura
* orientada a execucao real
* baseada em tools
* protegida por guards
* extensivel via skills
* e controlada integralmente pelo backend

