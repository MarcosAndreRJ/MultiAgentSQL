# Domain Rules - MultiAgent SQL

## Visao Geral

Este documento define regras e heuristicas default para agentes especialistas em MySQL no MultiAgent SQL.

Diretriz principal:

"As domain rules devem ser genericas, reutilizaveis e seguras para qualquer agente MySQL, sem assumir regras de negocio especificas de um sistema."

Este arquivo NAO deve conter:

- regras de negocio de um sistema especifico
- convencoes particulares de um cliente
- nomes reais de tabelas de um projeto
- padroes exclusivos de triggers de um ambiente

Esses detalhes pertencem a:

- prompt do agente
- skills do agente

---

## Objetivo

Fornecer uma base neutra para operacao em MySQL, ajudando o agente a:

- agir com seguranca
- consultar antes de afirmar
- gerar SQL mais consistente
- evitar acoes destrutivas indevidas
- manter comportamento previsivel

---

## Principio Central

As regras deste documento sao:

- defaults
- heuristicas
- guias de operacao

Nao sao verdades absolutas do banco do usuario.

Quando houver conflito entre:

- domain-rules default
- prompt do agente
- skills especificas
- estado real do banco

A prioridade deve ser:

1. estado real do banco
2. guard e validacao
3. prompt do agente
4. skills do agente
5. domain-rules default

---

## Dominio Estrategico: MySQL Executor Agents

### 1. Agentes MySQL executores

Caracteristicas:

- operam bancos reais
- precisam consultar schema real
- geram e executam SQL
- podem alterar estrutura e dados
- devem operar com seguranca

Riscos principais:

- inventar schema
- executar SQL destrutivo sem controle
- afirmar sucesso sem execucao real
- confiar demais em conhecimento estatico

Heuristicas:

- consultar antes de afirmar
- validar antes de executar
- pedir confirmacao em operacoes criticas
- responder sempre com base real

---

## Regras Default de Operacao MySQL

### 1. Read-first quando houver duvida estrutural

Se a tarefa depender de:

- existencia de tabela
- existencia de coluna
- definicao de indice
- definicao de trigger
- definicao de procedure
- relacao entre objetos

o agente deve primeiro consultar o banco.

Exemplos de introspecao recomendada:

- SHOW TABLES
- DESCRIBE
- SHOW CREATE TABLE
- INFORMATION_SCHEMA

---

### 2. Nao assumir schema por nome

O agente nao deve assumir que:

- uma tabela chamada `users` existe
- uma PK se chama `id`
- datas seguem certo padrao
- campos booleanos usam `is_`
- todas as tabelas possuem soft delete

Essas suposicoes podem existir em alguns sistemas, mas nao devem ser tratadas como verdade default.

---

### 3. Separar leitura, escrita e alteracao estrutural

Mentalmente, o agente deve diferenciar:

- leitura
- manipulacao de dados
- alteracao estrutural

Porque cada categoria possui risco diferente.

---

### 4. Confirmar operacoes destrutivas

Por padrao, devem ser consideradas operacoes sensiveis:

- DELETE
- DROP
- TRUNCATE
- UPDATE amplo
- ALTER TABLE potencialmente destrutivo
- DROP TRIGGER / PROCEDURE / FUNCTION / VIEW

Essas operacoes devem passar por guard.

---

### 5. Nao assumir suporte universal a recursos avancados

O agente nao deve assumir automaticamente:

- versao exata do MySQL
- suporte pleno a certos recursos avancados
- comportamento identico entre MySQL e MariaDB

Quando necessario, deve consultar versao e contexto do banco.

---

## Heuristicas Default para Geracao de SQL

### 1. Preferir SQL claro e explicito

Por padrao, preferir:

- nomes completos
- joins explicitos
- filtros claros
- aliases legiveis

Evitar SQL obscuro sem necessidade.

---

### 2. Evitar `SELECT *` quando o objetivo for estruturado

Se o objetivo exigir clareza ou controle de retorno, preferir colunas explicitas.

`SELECT *` pode ser aceitavel para exploracao inicial ou diagnostico rapido.

---

### 3. Preferir filtros em operacoes de escrita

Por padrao:

- UPDATE deve ter WHERE
- DELETE deve ter WHERE

Ausencia de WHERE deve elevar risco.

---

### 4. Em DDL, introspectar antes de alterar

Antes de:

- alterar tabela
- recriar view
- trocar trigger
- atualizar procedure

o agente deve verificar o estado atual do objeto.

---

### 5. Em mockdata, respeitar estrutura real

Ao gerar mockdata, o agente deve tentar respeitar:

- tipos de coluna
- nulabilidade
- FKs quando possivel
- cardinalidade basica

Mas sem assumir regras de negocio inexistentes.

---

## Heuristicas Default para Introspecao

### 1. Usar INFORMATION_SCHEMA quando ajudar

Quando necessario, o agente pode consultar:

- tables
- columns
- constraints
- routines
- triggers

---

### 2. Usar SHOW CREATE para definicao real

Quando o objetivo for entender implementacao atual de:

- tabela
- view
- trigger
- procedure
- function

preferir `SHOW CREATE` quando disponivel.

---

### 3. Evitar introspecao excessiva sem necessidade

Consultar o banco e obrigatorio quando necessario, mas nao repetir introspecao inutilmente no mesmo fluxo.

A memoria de sessao pode reduzir repeticao.

---

## Heuristicas Default para Execucao

### 1. O agente e executor assistido

Isso significa:

- ele pode operar o banco
- mas nunca executa fora da camada controlada do backend

---

### 2. Toda execucao deve ser rastreavel

Deve ser possivel identificar:

- agente
- banco
- SQL
- horario
- resultado
- necessidade ou nao de confirmacao

---

### 3. Nao afirmar sucesso antes do retorno real

Mesmo que o SQL pareca correto, o agente so pode declarar sucesso apos resposta real do backend.

---

## Heuristicas Default para Resposta

### 1. Explicar o que vai fazer

Quando houver SQL, o agente deve resumir a intencao.

---

### 2. Exibir o SQL

Por padrao, o SQL deve ser visivel ao usuario antes ou depois da execucao, conforme o fluxo.

---

### 3. Indicar status claramente

- nao executado
- pendente de confirmacao
- executado com sucesso
- falhou

---

### 4. Em erro, responder com clareza

Em caso de erro:

- nao esconder erro
- nao inventar causa
- nao fingir sucesso parcial

---

## Edge Cases Default

### Banco sem objetos esperados

Nao assumir erro do usuario.
Responder com base no que o banco realmente mostra.

---

### Comando ambiguo

Se houver ambiguidade real e a memoria nao resolver, pedir clarificacao ou mostrar opcoes.

---

### Varias acoes pendentes

Exigir identificacao clara da pendencia.

---

### SQL multi-statement

Tratar como potencialmente sensivel e delegar classificacao ao guard.

---

## O que Nao Fazer

- nao embutir regras de negocio especificas
- nao assumir nomenclatura de cliente
- nao assumir arquitetura do sistema alvo
- nao assumir convencoes de trigger de um projeto
- nao transformar heuristica default em verdade absoluta

---

## Integracao com Prompt e Skills

As domain-rules default servem como camada basica.

A especializacao real do agente deve vir de:

### Prompt do Agente
Exemplo:
- "voce e especialista no banco financeiro_x"

### Skills do Agente
Exemplo:
- naming conventions do projeto
- regras especificas de mockdata
- padroes de procedures do sistema

---

## Resumo

O `domain-rules.md` do MultiAgent SQL deve fornecer apenas uma base default e neutra para operacao em MySQL.

Ele existe para:

- melhorar comportamento padrao
- reduzir risco
- reforcar boas praticas genericas
- evitar suposicoes perigosas

Sem acoplar o sistema a regras de negocio ou convencoes de bancos especificos.

