# Memory - MultiAgent SQL

## Visao Geral

A memoria do MultiAgent SQL existe para sustentar uma interacao conversacional persistente entre usuario e agente, mantendo contexto suficiente para operacao real em banco de dados sem complicar desnecessariamente a implementacao.

Diretriz principal:

"A memoria deve ser simples, util, orientada por sessao e suficiente para manter continuidade operacional entre mensagens, especialmente em fluxos de introspecao, geracao de SQL, confirmacao de acoes e execucao real."

O foco nao e criar uma memoria sofisticada demais.

O foco e permitir que o agente:

- mantenha contexto entre mensagens
- lembre o banco ao qual esta vinculado
- saiba o que acabou de consultar
- preserve SQLs recentes
- acompanhe pendencias de confirmacao
- continue a tarefa sem perder coerencia

---

## Objetivo da Memoria

Permitir que cada agente:

- continue o raciocinio entre turnos
- mantenha coerencia sobre o schema em foco
- lembre skills ativas
- preserve operacoes recentes
- acompanhe pending actions
- responda refinamentos curtos sem recomecar do zero

Exemplos de continuidade que devem funcionar:

- "agora liste as views"
- "crie a trigger"
- "me mostre o ddl dela"
- "pode executar"
- "cancela"
- "gere mockdata para essa tabela"
- "agora faz o alter"

---

## Escopo da Memoria

A memoria deve ser organizada por:

- agente
- canal
- sessao/conversa

Exemplos de chave:

- `web:dba-devhacks:session-abc`
- `telegram:mysql-financeiro:123456789`
- `web:principal:session-x1`

Cada agente possui memoria isolada.

Nao existe memoria compartilhada automatica entre agentes.

---

## Tipos de Memoria

### 1. Memoria de Curto Prazo (turno atual)

Armazena apenas o necessario para processar a mensagem atual.

Conteudo tipico:

- intencao detectada
- SQL atual em analise
- tools chamadas no turno
- decisao do guard
- resultado do passo atual

Essa memoria e descartavel ao final do ciclo.

---

### 2. Memoria de Sessao por Conversa (principal)

Essa e a memoria mais importante do sistema.

Armazena estado recente da conversa entre usuario e agente.

Conteudo tipico:

- ultimas mensagens
- ultimo objetivo em andamento
- tabelas recentemente consultadas
- ultimo schema analisado
- ultimos SQLs gerados
- ultimos SQLs executados
- pending actions
- erros recentes relevantes
- skills ativas do agente naquela sessao
- preferencias do usuario naquela conversa

Essa memoria permite continuidade real entre turnos.

---

### 3. Memoria Operacional do Agente

Representa o contexto fixo ou semi-fixo do agente.

Conteudo tipico:

- agent_id
- nome do agente
- tipo do agente
- database vinculado
- prompt base
- lista de skills atribuídas
- politicas de guard
- configuracoes de permissao

Essa memoria nao depende do turno.
Ela e carregada sempre que a sessao usa aquele agente.

---

### 4. Memoria Persistente Leve (opcional)

Pode armazenar padroes uteis entre sessoes, sem virar um sistema de conhecimento complexo.

Conteudo tipico:

- tabelas frequentemente acessadas
- convencoes recorrentes
- objetos protegidos
- padroes de nomenclatura
- estrategias de mockdata ja aprovadas

Essa camada e opcional.
O sistema deve funcionar bem sem depender dela.

---

## Estrategia de Recuperacao

Prioridade de recuperacao:

1. contexto da mensagem atual
2. memoria de sessao por conversa
3. memoria operacional do agente
4. memoria persistente leve

Se houver conflito:

- prevalece a mensagem atual
- depois a sessao atual
- depois a configuracao estrutural do agente

---

## Estrategia de Atualizacao

Atualizar memoria quando:

- um novo SQL for gerado
- uma tool retornar dado relevante
- uma pending action for criada
- uma pending action for confirmada
- uma pending action for cancelada
- um objeto do banco entrar em foco
- o usuario mudar o objetivo da conversa
- uma operacao falhar e esse erro ainda for relevante no proximo turno

Evitar salvar:

- ruido
- repeticoes desnecessarias
- payload bruto grande sem necessidade
- respostas completas do LLM sem valor para continuidade

---

## Estrutura Minima Recomendada

```json
{
  "channel": "web|telegram",
  "conversation_id": "...",
  "agent_id": "...",
  "agent_type": "principal|mysql-specialist",
  "database": {
    "name": "devhacks_site"
  },
  "current_goal": "criar trigger para atualizar saldo",
  "active_skills": [
    "mysql-playbook",
    "naming-conventions"
  ],
  "recent_objects": {
    "tables": ["ContaFinanceira", "Transacao"],
    "views": [],
    "triggers": []
  },
  "last_sql_generated": "CREATE TRIGGER ...",
  "last_sql_executed": "SELECT * FROM ...",
  "pending_actions": [
    {
      "id": "pa_001",
      "summary": "executar DELETE em Transacao WHERE id = 10",
      "expires_at": "..."
    }
  ],
  "last_changes": [
    {
      "type": "tool_result",
      "summary": "tabela Transacao possui coluna dtPagamento"
    }
  ],
  "user_preferences": {
    "response_style": "objetivo"
  }
}
````

---

## Conteudos que Devem Ser Lembrados

### 1. Contexto do banco em foco

Quando o agente especialista estiver trabalhando em um banco, lembrar:

* nome do banco
* tabela em foco
* objeto em foco
* relacoes recentes descobertas

Isso ajuda a evitar introspecao repetitiva desnecessaria.

---

### 2. Ultimos SQLs

Guardar pelo menos:

* ultimo SQL gerado
* ultimo SQL executado
* ultimo SQL bloqueado pelo guard

Isso ajuda em pedidos como:

* "agora altera ele"
* "executa"
* "cancela esse"

---

### 3. Pending Actions

Esse e um item obrigatorio.

O agente deve lembrar:

* a acao pendente
* o SQL
* o resumo da acao
* o nivel de risco
* o prazo de expiracao

Sem isso, confirmacoes posteriores ficam inseguras.

---

### 4. Objetivo em andamento

Exemplo:

* "criar trigger de saldo"
* "gerar mockdata da tabela users"
* "analisar porque a procedure falha"

Essa informacao ajuda quando o usuario manda mensagens curtas como:

* "continua"
* "agora executa"
* "faz a view"

---

## Regras de Uso

### 1. Nao inventar memoria

O agente nao deve assumir contexto nao observado.

Se nao houver memoria valida, deve consultar tools ou pedir contexto.

---

### 2. Priorizar simplicidade

A memoria deve ser leve e funcional.

Nao precisa armazenar tudo.

---

### 3. Isolamento por agente

Cada agente tem sua propria memoria.

O agente principal nao herda automaticamente o contexto dos especialistas.
Um especialista nao herda automaticamente o contexto de outro.

---

### 4. Nao armazenar credenciais

A memoria nunca deve armazenar:

* senhas
* tokens
* credenciais completas
* segredos sensiveis

---

### 5. Guardar apenas o util

A memoria nao deve virar log bruto da conversa.

Guardar somente o que ajuda o proximo turno.

---

### 6. Permitir reset controlado

Deve existir forma de limpar o contexto da conversa:

* reset de sessao
* limpeza de pendencias expiradas
* reinicio do contexto conversacional

Sem derrubar o runtime.

---

## TTL e Limpeza

Recomenda-se:

* expirar pending actions apos periodo configurado
* resumir historico longo
* manter apenas ultimas N mensagens relevantes
* remover contexto operacional obsoleto

Exemplo:

* ultimas 10 a 20 mensagens resumidas
* ultimos 5 SQLs relevantes
* pending actions nao expiradas

---

## Edge Cases

### Primeiro turno sem contexto

Iniciar com estado vazio e seguir fluxo normal.

---

### Usuario muda de assunto bruscamente

Preservar historico, mas atualizar `current_goal`.

---

### Confirmacao apos expiracao

Nao executar.
Criar nova confirmacao.

---

### Varias acoes pendentes

Manter lista clara por ID.
Nao confirmar por ambiguidade.

---

### Troca de agente na interface

Iniciar sessao isolada para o novo agente.

---

## Seguranca

* nao armazenar credenciais
* nao armazenar dumps desnecessarios
* nao guardar dados sensiveis sem necessidade
* limpar pendencias expiradas
* evitar persistencia excessiva de resultados grandes

---

## Resumo

A memoria do MultiAgent SQL deve ser simples, isolada por agente e por conversa, e focada em continuidade operacional.

Ela existe para sustentar:

* multi-turno
* contexto de banco
* SQL recente
* objetos em foco
* pending actions
* consistencia entre consulta, validacao e execucao

Sem overengineering e sem transformar memoria em banco paralelo do sistema.
