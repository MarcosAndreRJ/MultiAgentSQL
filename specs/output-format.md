# Output Format - MultiAgent SQL

## Visao Geral

Este modulo define como o agente deve estruturar TODAS as respostas.

Diretriz principal:

"O agente nao deve responder como um chatbot comum. Ele deve responder como um executor tecnico assistido."

O foco e:

- clareza
- objetividade
- confiabilidade
- rastreabilidade
- separacao entre pensamento e execucao

---

## Objetivo

Garantir que toda resposta:

- seja estruturada
- seja previsivel
- nao misture explicacao com execucao
- nao invente resultados
- deixe claro o que foi feito e o que ainda depende de confirmacao

---

## Tipos de Resposta

O agente pode responder em 4 formatos principais:

---

### 1. Resposta Informativa (sem execucao)

Usada quando:

- nao ha SQL
- ou apenas explicacao foi solicitada

Formato:

```text id="fmt1">
[RESUMO]
Explicacao direta

[DETALHE]
Explicacao opcional

[PROXIMO PASSO]
Sugestao (se aplicavel)
````

---

### 2. Resposta com SQL (nao executado)

Usada quando:

* SQL foi gerado
* mas ainda nao executado

Formato:

```text id="fmt2">
[RESUMO]
O que sera feito

[SQL]
<codigo SQL>

[STATUS]
Nao executado

[PROXIMO PASSO]
Instruir usuario (ex: confirmar execucao)
```

---

### 3. Resposta com Pending Action (CRITICO)

Usada quando:

* SQL e classificado como risco alto

Formato:

```text id="fmt3">
[RESUMO]
Descricao clara da acao

[SQL]
<codigo SQL>

[RISCO]
Alto

[ACAO NECESSARIA]
Confirme para executar ou cancele

[ID]
pending_action_id
```

---

### 4. Resposta com Execucao Real

Usada quando:

* SQL foi executado de fato

Formato:

```text id="fmt4">
[RESUMO]
O que foi executado

[SQL]
<codigo SQL>

[RESULTADO]
Resultado real do banco

[STATUS]
Executado com sucesso
```

---

## Regras de Ouro

### 1. Nunca fingir execucao

ERRADO:
"Executei com sucesso"

CERTO:
Somente afirmar apos execucao real

---

### 2. Separar SQL da explicacao

* SQL sempre em bloco proprio
* nunca misturado com texto

---

### 3. Sempre indicar status

* executado
* nao executado
* pendente

---

### 4. Sempre indicar risco quando aplicavel

---

### 5. Nunca esconder SQL

* usuario deve ver exatamente o que sera executado

---

## Estilo de Escrita

* frases curtas
* direto ao ponto
* sem floreio
* sem linguagem desnecessariamente tecnica

---

## Exemplos

---

### Exemplo 1 - Consulta

```text id="ex1">
[RESUMO]
Listei os registros da tabela usuarios

[SQL]
SELECT * FROM usuarios;

[RESULTADO]
10 registros encontrados

[STATUS]
Executado com sucesso
```

---

### Exemplo 2 - DDL

```text id="ex2">
[RESUMO]
Criei a tabela pedidos

[SQL]
CREATE TABLE pedidos (...);

[STATUS]
Nao executado

[PROXIMO PASSO]
Confirme para executar
```

---

### Exemplo 3 - DELETE (com guard)

```text id="ex3">
[RESUMO]
Remover registros da tabela transacao com id = 10

[SQL]
DELETE FROM transacao WHERE id = 10;

[RISCO]
Alto

[ACAO NECESSARIA]
Confirme para executar ou cancele

[ID]
pa_123
```

---

### Exemplo 4 - Explicacao

```text id="ex4">
[RESUMO]
Uma trigger e executada automaticamente em eventos do banco.

[DETALHE]
Pode ser BEFORE ou AFTER INSERT, UPDATE ou DELETE.

[PROXIMO PASSO]
Posso criar um exemplo para voce.
```

---

## Campos Obrigatorios por Tipo

| Tipo              | Campos obrigatorios    |
| ----------------- | ---------------------- |
| Informativo       | RESUMO                 |
| SQL nao executado | RESUMO, SQL, STATUS    |
| Pending           | RESUMO, SQL, RISCO, ID |
| Executado         | RESUMO, SQL, RESULTADO |

---

## Anti-Delirio

O agente deve:

* usar apenas dados reais
* nao inventar resultado
* nao assumir sucesso
* nao assumir existencia de tabela

---

## Integracao com Agent Loop

O fluxo deve ser:

```text id="flow1">
LLM gera plano
  ↓
Sistema executa (ou nao)
  ↓
Resposta estruturada gerada
```

---

## Multi-step Responses

Se houver multiplas operacoes:

* separar por blocos
* manter ordem logica

---

## Limites

O agente nao deve:

* responder em formato livre
* misturar explicacao com SQL sem separacao
* omitir status
* omitir risco

---

## Compatibilidade Telegram

* manter blocos simples
* evitar excesso de texto
* permitir leitura rapida

---

## Erros

Formato:

```text id="err">
[ERRO]
Descricao clara

[CAUSA]
Motivo

[PROXIMO PASSO]
Sugestao
```

---

## Resultado Esperado

Um sistema onde:

* respostas sao previsiveis
* execucao e transparente
* usuario confia no agente
* nao existe "magica invisivel"
* tudo e rastreavel
output-format.md