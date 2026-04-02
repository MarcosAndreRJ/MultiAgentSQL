# PRD - MultiAgent SQL (Ollama + MySQL Executors)

## Visao Geral

O MultiAgent SQL e uma plataforma local em Python baseada em agentes independentes, projetada para operar bancos MySQL de forma assistida, segura e executavel.

Diretriz principal:

"O sistema deve operar como um runtime persistente orientado a eventos, permitindo interacao conversacional multi-turno via Web Chat e/ou Telegram, com agentes especializados capazes de executar operacoes reais em banco de dados sob controle de guards."

Diferente de assistentes passivos, os agentes deste sistema sao:

- executores tecnicos assistidos
- conectados diretamente a bancos reais
- controlados por regras de seguranca (guards)
- suportados por tools deterministicas
- configurados por prompt + skills

---

## Objetivo

Permitir que usuarios operem bancos MySQL de forma conversacional, com agentes especialistas capazes de:

- entender o contexto do banco
- consultar schema real
- gerar SQL coerente
- executar operacoes reais
- criar mock data
- manter e evoluir o banco

Tudo isso com:

- controle de risco
- confirmacoes para acoes criticas
- rastreabilidade
- comportamento anti-delirio

---

## Problema

Operar banco de dados exige:

- conhecimento tecnico elevado
- cuidado com acoes destrutivas
- entendimento do schema
- consistencia nas alteracoes

LLMs locais (como Ollama) possuem limitacoes:

- contexto reduzido
- tendencia a alucinacao
- dificuldade em manter coerencia estrutural

Sem controle adequado:

- podem inventar tabelas
- podem gerar SQL incorreto
- podem afirmar execucao sem executar
- podem causar dano real

---

## Solucao

Criar uma plataforma com:

### 1. Agentes independentes

- cada agente possui identidade propria
- cada agente pode ter:
  - prompt base (orientacao)
  - skills (conhecimento estruturado)
  - database vinculado (ou nao)

### 2. Dois tipos de agente

#### Agente Principal (Generalista)

- nao conectado a banco
- atua como:
  - arquiteto
  - revisor
  - orientador
- nao executa operacoes reais

#### Agentes Especialistas (DBA)

- conectados a um database especifico
- possuem acesso completo ao banco
- sao responsaveis por:
  - execucao real
  - manutencao
  - criacao de objetos
  - operacoes de dados

---

## Diferencial Central

O agente especialista NAO e apenas um chatbot.

Ele e:

> um executor tecnico assistido com acesso real ao banco, operando via tools controladas e protegido por guards.

---

## Funcionalidades Principais

### 1. Multiagentes independentes

- lista de agentes disponiveis
- selecao de agente por conversa
- cada agente com:
  - prompt proprio
  - skills associadas
  - configuracao de banco (quando aplicavel)

---

### 2. Suporte a Skills por agente

Cada agente pode possuir multiplas skills.

Uma skill e um arquivo `.md` com:

- instrucoes
- regras
- padroes
- conhecimento especifico

Exemplos:

- mysql-playbook
- naming-conventions
- ddl-rules
- business-rules
- mockdata-strategy

As skills ajudam o agente a:

- reduzir alucinacao
- seguir padroes do projeto
- entender melhor o dominio do banco

---

### 3. Prompt Base do Agente

Cada agente possui um prompt textual que define:

- seu papel
- seu comportamento
- o tipo de banco que ele opera
- restricoes

Esse prompt e complementado pelas skills.

---

### 4. Tools de Banco (obrigatorias e completas)

O sistema deve fornecer tools reais para:

#### Introspecao
- listar tabelas
- listar views
- listar triggers
- listar procedures
- descrever tabela
- obter DDL

#### Leitura
- SELECT
- SHOW
- EXPLAIN

#### Escrita
- INSERT
- UPDATE
- DELETE

#### Estrutura
- CREATE
- ALTER
- DROP
- TRUNCATE

#### Mock Data
- geracao coerente
- script ou execucao

---

### 5. Guard Engine (seguranca obrigatoria)

Toda acao critica deve passar por guards.

O guard deve:

- classificar SQL
- avaliar risco
- gerar resumo da acao
- criar pendencia
- solicitar confirmacao
- executar somente apos confirmacao

---

### 6. Pending Actions

Acoes criticas nao executam imediatamente.

Viram uma pendencia:

- aguardando confirmacao
- com timeout
- com contexto salvo

---

### 7. Execucao real controlada

Fluxo:

1. agente decide a acao
2. sistema valida
3. guard analisa
4. usuario confirma (se necessario)
5. backend executa
6. resultado real retorna
7. agente responde com base real

---

### 8. Anti-delirio (critico)

O sistema deve garantir:

- agente nao inventa schema
- agente consulta banco antes de afirmar
- agente nao finge execucao
- agente usa tools sempre que necessario

---

### 9. Interface Web

Baseada no layout fornecido:

- lista de agentes (esquerda)
- chat (centro)
- configuracoes (direita)
- gerenciador de skills
- preview de SQL
- confirmacao de acoes

---

### 10. CLI (secundaria)

Apenas para:

- debug
- execucao direta
- administracao

Nao substitui interface principal.

---

## Escopo

### Incluido

- multiagentes
- conexao MySQL
- tools completas
- guard engine
- skills por agente
- prompt por agente
- interface web
- CLI secundaria
- memoria de sessao simples

---

### Nao Incluido

- deploy cloud
- multi-tenant complexo
- RBAC avancado
- versionamento de schema automatico
- orchestracao entre agentes

---

## Requisitos Funcionais

- criar agentes
- vincular database a agente
- cadastrar skills
- atribuir skills ao agente
- editar prompt do agente
- conversar com agente
- executar operacoes no banco
- listar schema
- criar objetos
- modificar objetos
- deletar registros
- gerar mock data
- confirmar operacoes criticas
- visualizar historico

---

## Requisitos Nao Funcionais

- funcionamento offline (ollama local)
- baixa latencia
- previsibilidade
- controle de risco
- rastreabilidade
- logs estruturados
- simplicidade operacional
- modularidade

---

## Fluxo Principal

1. usuario seleciona agente
2. envia mensagem
3. sistema identifica intencao
4. agente consulta tools (se necessario)
5. agente gera plano/SQL
6. guard avalia
7. usuario confirma (se necessario)
8. execucao ocorre
9. resultado retorna
10. resposta final ao usuario

---

## Decisoes de Design

- agentes independentes
- skills como camada de conhecimento
- prompt + skill combinados
- tools deterministicas obrigatorias
- guard como camada central
- execucao nunca direta pelo LLM
- backend como autoridade final

---

## Edge Cases

- SQL invalido
- falha de conexao
- schema inconsistente
- confirmacao expirada
- multi-statement perigoso
- update/delete sem where
- tentativa de drop critico

---

## Metricas de Sucesso

- % de operacoes executadas com sucesso
- reducao de erros humanos
- reducao de SQL invalido
- zero execucoes destrutivas sem confirmacao
- consistencia entre resposta e banco real

---

## Seguranca

- nao expor credenciais
- uso de guards obrigatorio
- logs de execucao
- confirmacao para risco alto
- restricao por agente/database

---

## Futuras Evolucoes

- controle de permissao por tabela
- versionamento de schema
- rollback automatico
- auditoria avancada
- suporte a outros bancos (Postgres, etc)
- marketplace de skills

---

## Nome do Projeto

MultiAgent SQL

Alternativos:

- SQL Agents Runtime
- Local DBA Agents
- AgentDB
- SmartDB Agents

---

## Output Esperado

Uma plataforma funcional onde:

- cada agente opera seu banco
- skills orientam comportamento
- prompts definem especializacao
- tools executam operacoes reais
- guards garantem seguranca
- usuario controla tudo via chat
