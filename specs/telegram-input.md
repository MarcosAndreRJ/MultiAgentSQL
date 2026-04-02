# Telegram Input - MultiAgent SQL

## Visao Geral

Este modulo define como o sistema interpreta mensagens recebidas via Telegram (ou Web Chat equivalente).

Diretriz principal:

"O sistema deve entender mensagens curtas, comandos diretos e confirmações, sem exigir linguagem complexa do usuario."

O foco e:

- simplicidade
- robustez
- entendimento de contexto
- suporte a multi-turno

---

## Objetivo

Permitir que o usuario:

- converse naturalmente com o agente
- envie comandos diretos
- confirme operacoes criticas
- refine operacoes em andamento
- interaja sem precisar repetir contexto

---

## Tipos de Entrada

### 1. Pergunta / Comando Natural

Exemplos:

- "liste as tabelas"
- "mostra os registros de usuarios"
- "cria uma tabela de pedidos"
- "gera mockdata para clientes"
- "cria uma trigger para atualizar saldo"

---

### 2. Refinamento

Mensagens curtas que dependem do contexto:

- "agora faz a view"
- "adiciona indice"
- "usa a tabela transacao"
- "filtra por data"
- "faz com status ativo"

---

### 3. Confirmacao

Relacionadas a pending actions:

- "confirmar"
- "pode executar"
- "sim"
- "ok"
- "manda ver"

---

### 4. Cancelamento

- "cancelar"
- "nao"
- "para"
- "esquece isso"

---

### 5. Controle de fluxo

- "continua"
- "repete"
- "mostra de novo"
- "explica melhor"

---

### 6. Comandos de sistema

- "resetar conversa"
- "limpar contexto"
- "trocar agente"
- "listar agentes"

---

## Estrutura da Entrada

Toda mensagem deve ser transformada em um objeto padrao:

```json
{
  "raw_text": "...",
  "normalized_text": "...",
  "intent": "...",
  "agent_id": "...",
  "conversation_id": "...",
  "metadata": {}
}
````

---

## Normalizacao

Antes de qualquer processamento:

* remover acentos (opcional)
* padronizar minusculo
* remover espacos extras
* identificar palavras-chave

Exemplo:

"Pode executar isso?"

→

"pode executar isso"

---

## Classificacao de Intencao

O sistema deve classificar a entrada em uma das categorias:

```text id="u2d8kq"
- query
- write
- ddl
- explain
- mockdata
- confirm
- cancel
- control
- unknown
```

---

## Heuristicas de Classificacao

### Confirmacao

Se conter:

* confirmar
* pode executar
* sim
* ok

→ intent = confirm

---

### Cancelamento

Se conter:

* cancelar
* nao
* para
* esquece

→ intent = cancel

---

### Controle

Se conter:

* resetar
* limpar
* trocar agente

→ intent = control

---

### Caso contrario

→ enviar para LLM decidir (query / ddl / etc)

---

## Context Awareness

O sistema deve usar memoria para interpretar mensagens curtas.

Exemplo:

### Turno 1:

"cria uma tabela de pedidos"

### Turno 2:

"agora adiciona indice"

→ deve entender que o contexto e a tabela criada anteriormente

---

## Confirmacao de Pending Actions

Quando existir pending action:

Entrada:

"confirmar"

Fluxo:

1. buscar pending action ativa
2. validar expiracao
3. executar SQL
4. retornar resultado real

---

## Cancelamento de Pending Actions

Entrada:

"cancelar"

Fluxo:

1. localizar pending action
2. marcar como cancelada
3. responder ao usuario

---

## Prioridade de Interpretacao

1. pending action ativa
2. comandos diretos (confirm/cancel)
3. contexto da sessao
4. interpretacao via LLM

---

## Tratamento de Ambiguidade

Se houver mais de uma pending action:

Resposta:

"Existe mais de uma acao pendente. Informe qual deseja confirmar (ID)."

---

## Multi-turno

O sistema deve permitir:

* continuidade
* refinamento incremental
* comandos incompletos

---

## Fallback

Se nao entender:

Resposta:

"Não entendi completamente. Pode reformular?"

---

## Edge Cases

### Confirmacao sem pending action

Resposta:

"Nao existe nenhuma acao pendente para confirmacao."

---

### Cancelamento sem pending action

Resposta:

"Nao existe nenhuma acao pendente para cancelar."

---

### Mensagem vazia

Ignorar ou pedir nova entrada

---

### Entrada muito longa

* truncar com cuidado
* manter contexto essencial

---

## Integracao com Agent Loop

Fluxo:

```text id="r5n2k1"
Mensagem recebida
  ↓
Normalizacao
  ↓
Classificacao de intencao
  ↓
Verificacao de pending action
  ↓
Encaminhar para agent loop
```

---

## Regras Criticas

### 1. Confirmacao nunca passa pelo LLM

* confirmacao deve ir direto para execution service

---

### 2. Cancelamento nunca passa pelo LLM

* deve ser tratado diretamente

---

### 3. Nao depender do usuario ser tecnico

* aceitar linguagem simples

---

### 4. Priorizar contexto

* interpretar mensagens curtas corretamente

---

## Compatibilidade Web Chat

As mesmas regras devem funcionar no Web Chat.

Telegram e apenas um canal.

---

## Seguranca

* validar origem da mensagem (Telegram user_id)
* evitar execucao nao autorizada
* nao aceitar comandos fora do escopo

---

## Resultado Esperado

Um sistema que:

* entende linguagem natural
* responde a comandos curtos
* permite confirmacoes seguras
* sustenta conversas multi-turno
* reduz friccao para o usuario
