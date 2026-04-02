# Agent Loop - MultiAgent SQL

## Visao Geral

O Agent Loop define como um agente processa uma mensagem do usuario do inicio ao fim.

Diretriz principal:

"O agente nao responde diretamente. Ele pensa, consulta, valida, e somente depois responde com base em dados reais."

Cada mensagem passa por um ciclo controlado.

---

## Objetivo

Garantir que o agente:

- nao alucine
- nao invente dados
- nao execute sem controle
- use tools quando necessario
- produza respostas confiaveis

---

## Estrutura do Loop

```text
Mensagem do usuario
  ↓
Construir contexto
  ↓
Gerar plano (LLM)
  ↓
Executar tools (se necessario)
  ↓
Validar com guard (se necessario)
  ↓
Executar acao (se permitido)
  ↓
Responder usuario
````

---

## Etapas Detalhadas

### 1. Receber mensagem

Entrada:

* texto do usuario
* agent_id
* session_id

---

### 2. Construir contexto

O sistema deve montar:

* historico recente (limitado)
* prompt base do agente
* skills do agente
* contexto da sessao

Resultado:

```text
PROMPT FINAL = prompt_base + skills + contexto + mensagem
```

---

### 3. Gerar plano (LLM)

O agente nao responde ainda.

Ele gera um plano estruturado.

Formato esperado:

```json
{
  "intent": "query | write | ddl | explain | mockdata | unknown",
  "needs_tools": true,
  "tools": [
    {
      "name": "db_introspection | db_read | db_write | db_ddl | db_mockdata",
      "action": "...",
      "input": {}
    }
  ],
  "sql": "...",
  "explanation": "...",
  "risk_hint": "low | medium | high"
}
```

---

### 4. Decisao de execucao

Se:

* `needs_tools = false` → responder direto
* `needs_tools = true` → executar tools

---

### 5. Execucao de tools

O sistema:

* chama tool correta
* passa parametros
* recebe resultado real

Exemplo:

```text
Tool: db_introspection.list_tables
Resultado: ["users", "orders"]
```

---

### 6. Replanejamento (se necessario)

Se a primeira execucao nao for suficiente:

* agente pode rodar outro ciclo interno
* ex: introspecao → depois SELECT

---

### 7. Validacao com Guard

Se houver SQL:

* classificar tipo
* avaliar risco

---

### 8. Classificacao de risco

```text
LOW:
- SELECT
- SHOW

MEDIUM:
- INSERT
- UPDATE com WHERE

HIGH:
- DELETE
- DROP
- TRUNCATE
- UPDATE sem WHERE
```

---

### 9. Fluxo de execucao

#### Caso LOW

* executa direto

#### Caso MEDIUM

* pode executar direto (configuravel)

#### Caso HIGH

* criar pending action
* NAO executar

---

### 10. Pending Action

Estrutura:

```json
{
  "id": "...",
  "sql": "...",
  "summary": "Remover todos os registros da tabela X",
  "risk": "high"
}
```

---

### 11. Confirmacao do usuario

Usuario responde:

* "confirmar"
* "cancelar"

---

### 12. Execucao final

Se confirmado:

* executar SQL real
* capturar resultado

---

### 13. Resposta final

O agente deve responder:

* com base em dados reais
* de forma clara
* sem linguagem tecnica desnecessaria

---

## Regras Criticas

### 1. Nunca inventar schema

ERRADO:
"Existe uma tabela chamada clientes"

CERTO:
Consultar via tool antes

---

### 2. Nunca fingir execucao

ERRADO:
"Executei com sucesso"

CERTO:
Executar via backend e retornar resultado

---

### 3. Nunca executar sem guard

* DELETE sem confirmacao = proibido

---

### 4. Nunca assumir sucesso

Sempre validar retorno

---

### 5. Sempre usar tools quando necessario

* nao confiar em memoria do modelo

---

## Multi-step Loop

Algumas operacoes exigem varios passos:

```text
Pergunta:
"Crie uma tabela de pedidos baseada na tabela users"

Loop:

1. introspecao (users)
2. gerar DDL
3. validar
4. executar (com confirmacao)
```

---

## Tratamento de Erros

### SQL invalido

* capturar erro
* retornar mensagem clara

---

### Falha de conexao

* informar indisponibilidade

---

### Timeout LLM

* retry simples
* fallback

---

## Estrutura Interna

```python
def agent_loop(message, agent, session):
    context = build_context(agent, session, message)

    plan = call_llm(context)

    if not plan.needs_tools:
        return plan.explanation

    result = execute_tools(plan.tools)

    if plan.sql:
        risk = classify_sql(plan.sql)

        if risk == "high":
            create_pending_action(plan.sql)
            return "Preciso de confirmacao..."

        execution = run_sql(plan.sql)

        return format_response(execution)

    return format_response(result)
```

---

## Anti-loop infinito

* limitar numero de ciclos internos
* ex: max 3 steps

---

## Persistencia

Salvar:

* mensagens
* SQL executado
* erros
* pendencias

---

## Resultado Esperado

Um agente que:

* pensa antes de agir
* consulta antes de afirmar
* executa com controle
* responde com base real
* evita alucinacao
* protege o banco

