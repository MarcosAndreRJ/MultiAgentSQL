# Tools - MultiAgent SQL

## Visao Geral

Este modulo define as ferramentas (tools) que permitem ao agente interagir com o banco de dados de forma real, controlada e eficiente.

Diretriz principal:

"As tools devem ser flexiveis o suficiente para permitir execucao real de SQL sem friccao, mas seguras o suficiente para impedir execucoes indevidas."

O agente nao deve:

- simular execucao
- montar resultados ficticios
- depender de heuristica para dados reais

Ele deve:

> usar tools reais para ler e executar no banco.

---

## Objetivo

Permitir que os agentes:

- consultem schema real
- executem SQL livre
- criem e alterem estruturas
- manipulem dados
- gerem mock data
- operem com fluidez

Sem limitar artificialmente o que o agente pode fazer.

---

## Principio Central

### Tool unica e poderosa (core)

Ao inves de fragmentar demais, o sistema deve possuir uma tool principal:

```text
db_execute
````

Que permite executar qualquer SQL valido.

---

## db_execute (CORE TOOL)

### Descricao

Executa SQL diretamente no banco associado ao agente.

### Entrada

```json
{
  "sql": "string",
  "params": {},
  "mode": "read | write | ddl",
  "dry_run": false
}
```

---

### Comportamento

* executa SQL como esta
* suporta:

  * SELECT
  * INSERT
  * UPDATE
  * DELETE
  * CREATE
  * ALTER
  * DROP
  * TRUNCATE
  * procedures
  * multi-statements (configuravel)

---

### Saida

```json
{
  "success": true,
  "rows": [],
  "rows_affected": 0,
  "execution_time_ms": 12,
  "error": null
}
```

---

### Regras

* NAO faz validacao de risco → isso e responsabilidade do guard
* NAO altera SQL → executa exatamente o que recebeu
* sempre retorna resultado real

---

## Tools Auxiliares (Opcional, mas recomendadas)

Para melhorar performance e reduzir carga no LLM.

---

### 1. db_introspect

#### Descricao

Consulta estrutura do banco.

#### Funcoes

* list_tables
* list_views
* list_triggers
* describe_table
* show_create_table

---

### 2. db_read

Wrapper para SELECT.

Pode usar db_execute internamente.

---

### 3. db_schema_cache

Cache de schema recente.

Evita introspecao repetida.

---

### 4. db_mockdata

Gera dados ficticios coerentes.

Entrada:

```json
{
  "table": "usuarios",
  "rows": 100
}
```

---

### 5. sql_explain

Executa EXPLAIN para queries.

---

## Por que nao quebrar demais as tools?

Evitar:

* excesso de ferramentas
* interfaces complexas
* rigidez desnecessaria

Problema comum:

> LLM trava porque nao sabe qual tool usar

Solucao:

* poucas tools
* bem definidas
* poderosas

---

## Fluxo Ideal

```text
Agente gera SQL
  ↓
Guard analisa
  ↓
Se permitido:
  ↓
db_execute(SQL)
  ↓
Resultado real
```

---

## Flexibilidade (Ponto-chave do seu projeto)

A tool deve permitir:

### 1. SQL livre

* nao limitar tipo de comando
* nao restringir estrutura

---

### 2. Multi-statement (opcional)

Exemplo:

```sql
START TRANSACTION;
UPDATE contas SET saldo = saldo - 100 WHERE id = 1;
UPDATE contas SET saldo = saldo + 100 WHERE id = 2;
COMMIT;
```

---

### 3. Procedures e Functions

* CALL procedure()
* CREATE FUNCTION
* etc

---

### 4. Queries complexas

* JOINs
* subqueries
* CTE (quando suportado)

---

## Integracao com Guard

IMPORTANTE:

A tool nao decide nada.

Ela:

* executa

Quem decide:

* guard engine

---

## Integracao com Validation

Antes de chamar db_execute:

* SQL deve ser validado
* risco classificado

---

## Anti-Delirio

O agente deve:

* usar db_execute para obter dados reais
* nunca inventar resultado
* nunca responder sem consultar quando necessario

---

## Erros

A tool deve capturar:

* erro SQL
* erro de conexao
* timeout

Retornar:

```json
{
  "success": false,
  "error": "mensagem clara"
}
```

---

## Transacoes

Modo avancado (futuro):

* begin
* commit
* rollback

Inicialmente:

* auto-commit simples

---

## Segurança

A tool deve:

* usar conexao isolada por agente
* nao expor credenciais
* limitar acesso ao database configurado
* impedir comandos fora do escopo (ex: sistema operacional)

---

## Performance

* limitar tamanho de retorno
* paginar SELECTs grandes (opcional)
* evitar travamento do runtime

---

## Edge Cases

### SQL muito grande

* truncar log
* executar normalmente

---

### Resultado muito grande

* limitar retorno
* avisar usuario

---

### Multi-statement perigoso

* delegar ao guard

---

## O que NAO fazer

* nao criar dezenas de tools pequenas
* nao bloquear SQL valido sem motivo
* nao alterar SQL do agente sem transparencia
* nao executar sem passar pelo guard
* nao esconder erro

---

## Resultado Esperado

Um sistema onde:

* o agente tem liberdade para operar
* o backend mantém controle
* SQL flui sem friccao
* execucao e real
* risco e controlado fora da tool

