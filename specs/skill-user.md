# Skill System - MultiAgent SQL

## Visao Geral

As skills sao blocos de conhecimento estruturado que complementam o prompt base do agente.

Diretriz principal:

"As skills nao substituem o agente. Elas orientam o agente."

Cada skill e um arquivo `.md` contendo:

- regras
- instrucoes
- padroes
- exemplos
- restricoes

---

## Objetivo

Permitir que os agentes:

- reduzam alucinacao
- sigam padroes do projeto
- respeitem regras de negocio
- gerem SQL consistente
- operem de forma previsivel

---

## Relacao Prompt + Skills

O comportamento do agente e definido por:

```text
PROMPT FINAL =
prompt_base do agente
+ skills atribuídas
+ contexto da sessao
+ mensagem do usuario
````

---

## O que uma Skill pode conter

Uma skill pode incluir:

* padroes de nomenclatura
* convencoes SQL
* regras de negocio
* estrutura de tabelas
* boas praticas
* proibicoes
* exemplos reais
* templates de SQL
* estrategias de mockdata

---

## O que uma Skill NAO deve fazer

* nao executar codigo
* nao chamar tools diretamente
* nao assumir dados inexistentes
* nao substituir o agent-loop
* nao conter logica procedural

---

## Estrutura Recomendada de uma Skill

```text
# Nome da Skill

## Objetivo
Explicar para que a skill serve

## Regras
Lista de regras obrigatorias

## Padroes
Convencoes que devem ser seguidas

## Proibicoes
O que o agente nao pode fazer

## Exemplos
Exemplos concretos

## Observacoes
Notas adicionais
```

---

## Exemplo de Skill (MySQL Naming)

```text id="ex1">
# MySQL Naming Conventions

## Objetivo
Padronizar nomes de tabelas e colunas.

## Regras
- nomes em snake_case
- tabelas no singular
- colunas descritivas

## Padroes
- id_tabela
- dt_criacao
- dt_atualizacao
- is_ativo

## Proibicoes
- nao usar camelCase
- nao usar abreviacoes confusas

## Exemplos
- usuario
- pedido_item
- dt_pagamento
```

---

## Tipos de Skills

### 1. Tecnicas

* mysql-playbook
* ddl-rules
* indexing-strategy
* performance-tuning

---

### 2. Dominio de Negocio

* regras financeiras
* regras de faturamento
* regras de estoque

---

### 3. Mock Data

* estrategia de dados ficticios
* distribuicao realista
* relacionamentos coerentes

---

### 4. Seguranca

* operacoes proibidas
* tabelas criticas
* restricoes de escrita

---

## Como as Skills Influenciam o Agente

As skills:

* aumentam confiabilidade
* reduzem improviso
* guiam decisoes
* ajudam na geracao de SQL

Mas:

> O agente ainda decide. A skill nao decide por ele.

---

## Ordem de Prioridade

Quando houver conflito:

1. mensagem do usuario
2. guard engine (seguranca)
3. prompt base do agente
4. skills
5. memoria

---

## Boas Praticas

### 1. Skills pequenas e especificas

Evitar:

* skills gigantes
* conhecimento misturado

Preferir:

* varias skills menores

---

### 2. Nome claro

Exemplos:

* mysql-ddl-rules
* financial-transactions-rules
* mockdata-ecommerce

---

### 3. Foco unico

Cada skill deve resolver um problema.

---

### 4. Evitar redundancia

Nao repetir regras em varias skills.

---

### 5. Usar exemplos reais

Isso melhora muito o comportamento do LLM.

---

## Associacao de Skills ao Agente

Cada agente pode ter varias skills.

Exemplo:

```yaml
agent:
  name: mysql-devhacks
  skills:
    - mysql-playbook
    - ddl-rules
    - mockdata-strategy
```

---

## Carregamento das Skills

O sistema deve:

1. ler arquivos `.md`
2. concatenar conteudo
3. anexar ao prompt base

---

## Atualizacao de Skills

Skills podem ser:

* editadas
* adicionadas
* removidas

Sem reiniciar o sistema (idealmente).

---

## Anti-Delirio com Skills

Skills ajudam a evitar:

* nomes errados de tabela
* SQL fora do padrao
* regras de negocio quebradas

Mas nao substituem:

* introspecao real
* uso de tools

---

## Interacao com Guard

Mesmo que a skill permita algo:

* o guard sempre prevalece

Exemplo:

Skill diz:
"Pode deletar registros antigos"

Guard diz:
"DELETE detectado → precisa confirmacao"

Resultado:
→ confirmacao obrigatoria

---

## Exemplo Real (DDL Rules)

```text id="ex2">
# MySQL DDL Rules

## Regras
- sempre usar ENGINE=InnoDB
- usar charset utf8mb4
- sempre definir PRIMARY KEY
- evitar campos NULL quando possivel

## Proibicoes
- nao criar tabela sem PK
- nao usar MyISAM

## Exemplo
CREATE TABLE usuario (
  id_usuario INT PRIMARY KEY AUTO_INCREMENT,
  nome VARCHAR(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Edge Cases

### Skills conflitantes

Resolver via prioridade:

* prompt base > skill

---

### Skill desatualizada

Nao confiar cegamente.
Validar via tools quando necessario.

---

### Skill muito generica

Pode gerar comportamento impreciso.

---

## Seguranca

* skills nao devem conter credenciais
* nao devem conter SQL destrutivo como padrao
* nao devem instruir bypass de guard

---

## Resultado Esperado

Um sistema onde:

* agentes sao configuraveis via skills
* comportamento e previsivel
* SQL segue padrao
* regras de negocio sao respeitadas
* alucinacao e reduzida
