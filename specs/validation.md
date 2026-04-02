# Validation - MultiAgent SQL

## Visao Geral

Este documento define as validacoes obrigatorias do MultiAgent SQL para garantir operacao segura, previsivel e confiavel.

Diretriz principal:

"O sistema deve validar antes de executar. Em caso de duvida, deve consultar, bloquear ou pedir confirmacao."

O objetivo da validacao nao e burocracia.
O objetivo e impedir:

- alucinacao
- execucao indevida
- respostas falsas
- SQL perigoso sem controle
- perda de contexto

---

## Objetivo

Garantir que:

- o agente use dados reais
- o SQL seja analisado antes de executar
- acoes criticas sejam protegidas
- a resposta final reflita o resultado real
- a memoria e o contexto estejam coerentes
- skills orientem, mas nao contornem regras de seguranca

---

## Principios de Validacao

### 1. Validar antes de afirmar

O agente nao deve afirmar existencia de:

- tabela
- coluna
- view
- trigger
- procedure
- function
- dado

sem consultar o banco quando isso depender do estado real.

---

### 2. Validar antes de executar

Todo SQL precisa ser classificado antes da execucao.

---

### 3. Validar antes de confirmar sucesso

O agente so pode dizer que algo foi executado com sucesso apos retorno real do backend.

---

### 4. Guard sempre prevalece

Mesmo que:

- o prompt permita
- a skill sugira
- o usuario insista

o guard continua sendo autoridade para acoes criticas.

---

## Camadas de Validacao

### 1. Validacao de Entrada

Verificar:

- agent_id existe
- sessao existe ou pode ser criada
- mensagem nao esta vazia
- origem autorizada
- comando especial valido

Falhas devem retornar erro claro.

---

### 2. Validacao de Contexto

Verificar:

- agente correto esta selecionado
- agente possui database se a tarefa exigir banco
- pending action existe para confirmacao/cancelamento
- pending action nao expirou
- contexto da sessao nao esta ambiguo

---

### 3. Validacao de Plano do LLM

Toda saida estruturada do LLM deve ser validada pelo backend.

Campos minimos esperados:

- intent
- needs_tools
- sql quando houver
- explanation
- risk_hint

O backend nao deve confiar cegamente no JSON do LLM.

Deve validar:

- formato
- coerencia
- tipo da operacao
- compatibilidade com agente

---

### 4. Validacao de Tool Calls

Antes de executar tool:

- nome da tool deve existir
- acao deve ser suportada
- payload deve ser valido
- tool deve ser permitida para aquele agente

Exemplo:

- agente principal nao pode chamar tool de escrita em banco
- agente sem database nao pode usar db_read/db_write/db_ddl

---

### 5. Validacao de SQL

Todo SQL deve passar por classificador e analisador.

Verificar pelo menos:

- tipo principal do SQL
- multi-statement
- DELETE sem WHERE
- UPDATE sem WHERE
- DROP
- TRUNCATE
- ALTER destrutivo
- uso de comandos nao suportados
- compatibilidade basica com MySQL

---

### 6. Validacao de Guard

O sistema deve verificar:

- nivel de risco
- politica do agente
- necessidade de confirmacao
- volume estimado quando possivel
- objeto afetado quando possivel

---

### 7. Validacao de Execucao

Antes da execucao real:

- conexao com banco disponivel
- transaction/connection valida
- SQL final definido
- acao autorizada
- confirmacao presente quando obrigatoria

---

### 8. Validacao de Resposta Final

Antes de responder ao usuario, garantir que:

- status esta correto
- SQL exibido e o SQL real
- resultado corresponde ao retorno do backend
- nao ha afirmacao falsa de sucesso
- pending action foi mencionada corretamente quando aplicavel

---

## Validacoes Obrigatorias de Anti-Delirio

### 1. Schema Real Obrigatorio

Se a resposta depende do estado do banco, o agente deve consultar tools reais.

Exemplos:

#### ERRADO
"A tabela users possui coluna email"

#### CERTO
Consultar `list_columns` ou `describe_table` antes

---

### 2. Execucao Real Obrigatoria

Se o agente disser:

- executei
- criei
- alterei
- deletei
- atualizei

entao deve existir execucao real registrada.

---

### 3. Resultado Real Obrigatorio

Se o agente informar:

- quantidade de registros
- nome de tabelas
- estrutura
- sucesso de comando

isso deve vir de retorno real do sistema, nao de estimativa solta do modelo.

---

### 4. Introspecao Antes de DDL Relevante

Se o usuario pedir algo como:

- criar tabela relacionada
- alterar trigger existente
- ajustar procedure
- gerar mockdata coerente

o sistema deve consultar contexto real antes, sempre que fizer sentido.

---

## Validacoes de Skills

### 1. Skill nao substitui tool

Mesmo que uma skill diga:

- "a tabela principal e Transacao"

o agente ainda deve confirmar quando a operacao depender do estado atual do banco.

---

### 2. Skill nao pode contornar guard

Se uma skill disser:

- "delete pode executar direto"

mas a politica do guard exigir confirmacao,
a confirmacao continua obrigatoria.

---

### 3. Skill deve ser carregavel e legivel

Verificar:

- arquivo existe
- conteudo nao esta vazio
- encoding legivel
- tamanho razoavel

---

## Validacoes de Pending Actions

### 1. Criacao valida

Ao criar pending action, garantir:

- SQL existe
- risco e alto ou exige confirmacao
- resumo foi gerado
- expiracao foi definida
- agente e sessao foram vinculados

---

### 2. Confirmacao valida

Ao confirmar:

- pending action existe
- pertence ao agente/sessao correta
- nao expirou
- nao foi cancelada
- nao foi executada antes

---

### 3. Cancelamento valido

Ao cancelar:

- pending action existe
- ainda esta pendente

---

### 4. Expiracao

Acoes expiradas nao podem executar.
Devem exigir nova geracao/confirmacao.

---

## Validacoes de Qualidade

### Clareza

A resposta deve ser compreensivel para humano.

---

### Rastreabilidade

Deve ser possivel saber:

- qual agente respondeu
- qual SQL foi gerado
- se executou
- se havia risco
- se houve confirmacao

---

### Consistencia

Nao pode haver contradicao entre:

- status
- SQL
- resultado
- memoria da sessao

---

## Sinais de Problema

Revisar/bloquear quando houver:

- agente afirmando existencia de estrutura sem introspecao
- SQL destrutivo sem pending action
- confirmacao vaga com varias pendencias
- resposta dizendo "executado" sem log de execucao
- LLM tentando chamar tool inexistente
- skill conflitando com guard
- contexto de sessao incoerente
- tentativa de executar comando fora do escopo MySQL permitido

---

## Processo de Validacao

```text
Mensagem recebida
  ↓
Validacao de entrada
  ↓
Validacao de contexto
  ↓
Plano do LLM
  ↓
Validacao do plano
  ↓
Tool calls / SQL
  ↓
Classificacao SQL
  ↓
Guard
  ↓
Execucao real (se permitido)
  ↓
Validacao da resposta final
  ↓
Entrega
````

---

## O que Nao Fazer

* nao confiar cegamente no LLM
* nao executar SQL sem classificar
* nao tratar confirmacao de forma ambigua
* nao permitir bypass do guard
* nao responder com base em "acho que"
* nao transformar skills em fonte absoluta da verdade
* nao deixar memoria antiga contaminar nova sessao sem controle

---

## Nivel de Rigor

### Simples

* validacao de entrada
* validacao de SQL
* guard basico

### Intermediario

* mais checks de contexto
* pending actions robustas
* validacao de resposta final

### Avancado

* estimativa de impacto
* objetos protegidos
* validacao por tabela critica
* regras customizadas por agente

O sistema deve permitir evoluir entre esses niveis sem reescrever o core.

---

## Resumo

Validation no MultiAgent SQL existe para garantir que o sistema opere como executor tecnico assistido, e nao como chatbot improvisado.

Ele protege contra:

* alucinacao
* execucao indevida
* respostas falsas
* confirmacoes inseguras
* uso incorreto de skills

A regra central e simples:

consultar quando precisar, validar antes de executar e responder apenas com base no que realmente aconteceu.

