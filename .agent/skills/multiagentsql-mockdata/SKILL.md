---
name: multiagentsql-mockdata
description: >
  Skill especialista em criação de configurações YAML para agentes de mockdata no projeto MultiAgentSQL.
  Catálogo de tipos suportados pela ferramenta db_mockdata, padrões de seed SQL e regras de dependência de FK.
  Use quando estiver criando agentes de mockup, gerando seeds ou planejando pipelines de dados de teste.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Skill: MultiAgentSQL Mockdata

> **Princípio central:** Dados de teste precisam ser plausíveis, no idioma correto (pt-BR) e respeitar as FKs do schema.

---

## Capacidades do `db_mockdata.py`

A ferramenta nativa `db_mockdata` do projeto gera dados automaticamente baseados na **introspecção real da tabela**.

### Como funciona

1. `DESCRIBE <tabela>` → obtém campos, tipos, extras (AUTO_INCREMENT, NULL)
2. Filtra colunas AUTO_INCREMENT (não são inseridas)  
3. Gera valor por tipo de dado e nome de coluna
4. Constrói `INSERT INTO ... VALUES (...), (...)`
5. Executa com `mode="write"` via `db_execute`

### Limite de segurança
- Máximo de **100 linhas por chamada** (`min(rows, 100)`)
- Para volumes maiores → use múltiplas chamadas ou SQL manual com loop

---

## Catálogo de Tipos Suportados

| Tipo MySQL | Estratégia de Geração |
|---|---|
| `INT`, `BIGINT` | Baseado no nome da coluna (FK → 1–100, idade → 18–80, qtd → 1–500) |
| `TINYINT(1)` | Booleano: 0 ou 1 |
| `DECIMAL`, `FLOAT`, `DOUBLE` | `random.uniform(1.0, 9999.99)` arredondado a 2 casas |
| `VARCHAR(n)`, `CHAR(n)` | Baseado no nome da coluna (veja heurísticas abaixo) |
| `TEXT`, `LONGTEXT`, `MEDIUMTEXT` | Texto de 3 a 8 palavras genéricas |
| `DATETIME`, `TIMESTAMP` | Datas aleatórias entre 2024-01-01 e 2025-12-31 |
| `DATE` | Datas aleatórias entre 2024-01-01 e 2025-12-31 |
| `TIME` | Horário aleatório `HH:MM:00` |
| `YEAR` | Entre 2020 e 2025 |
| `ENUM(...)` | Escolha aleatória das opções definidas no schema |
| `JSON` | `{"mock": true}` |
| Outros | `mock_<sufixo_aleatorio>` |

---

## Heurísticas por Nome de Coluna (VARCHAR/CHAR)

A ferramenta detecta esses padrões **automaticamente** no nome do campo:

| Padrão no nome | Valor gerado |
|---|---|
| `nome`, `name`, `first` | Nome pt-BR: Ana, Carlos, Maria... |
| `sobrenome`, `lastname`, `surname` | Sobrenome pt-BR: Silva, Santos... |
| `email` | `nome123@gmail.com` |
| `telefone`, `phone`, `celular` | `(11) 9XXX-XXXX` |
| `cep`, `zip` | `XXXXX-XXX` |
| `cpf` | `XXX.XXX.XXX-XX` |
| `descricao`, `description`, `obs` | Texto aleatório |
| `cidade`, `city` | Capitais br: São Paulo, Rio de Janeiro... |
| `status` | `ativo`, `inativo`, `pendente` |

---

## Padrão para Seed SQL Manual (volumes > 100 ou com dependências)

Quando o volume é maior ou as dependências de FK precisam ser controladas, gere SQL manual:

```sql
-- Ordem de inserção: SEMPRE filhos após pais

-- 1. Tabelas sem FK (entidades pai)
INSERT INTO `Empresa` (`Nome`, `CNPJ`, `Email`) VALUES
  ('Empresa Alpha', '12.345.678/0001-90', 'alpha@empresa.com.br'),
  ('Empresa Beta', '98.765.432/0001-10', 'beta@empresa.com.br');

-- 2. Tabelas com FK para entidades pai
INSERT INTO `Projeto` (`Titulo`, `Empresa_id`, `Status`, `DataInicio`) VALUES
  ('Projeto Web', 1, 'Ativo', '2024-03-01'),
  ('Projeto Mobile', 2, 'Pendente', '2024-06-15');
```

---

## Regras de Dependência de FK

```
SEMPRE inserir na ordem: TabSemFK → Tab1FK → Tab2FK → TabNFK

EXEMPLO:
  Empresa (sem FK) → Projeto (FK: Empresa_id) → Atividade (FK: Projeto_id)
```

Para descobrir a ordem: `SHOW CREATE TABLE <tabela>` ou via digest do agente.

---

## Processo de Geração de Seed num Agente de Mockup

1. **Introspect** → Carregar digest ou `DESCRIBE` das tabelas alvos
2. **Mapear dependências** → Identificar FKs e montar grafo de dependência
3. **Ordernar inserção** → Topological sort das tabelas
4. **Gerar dados**: 
   - Tabelas simples → usar `db_mockdata` nativo (até 100 linhas)
   - Tabelas com FKs complexos → SQL manual com IDs cruzados
5. **Verificar** → `SELECT COUNT(*) FROM <tabela>` após inserção

---

## Pontos de Atenção ao Criar um Agente de Mockdata

> [!WARNING]
> Nunca adicionar `DELETE` ou `DROP` no `auto_approve` de um agente de mockup.
> Mockdata é dado falso mas pode sobrescrever dados reais se o banco for o de produção.

> [!IMPORTANT]
> O campo `prompt_file` no YAML deve apontar para um arquivo existente em `config/prompts/`.
> Use o mesmo `id` do agente + `.md` como convenção.

> [!TIP]
> Para agentes de demonstração ou CI/CD, configure `can_ddl: true` para o agente poder criar
> tabelas de teste (como `_test_usuarios`) sem afetar o schema principal.

---

## Template Rápido de Prompt para Agente de Mockdata

Salvar em `config/prompts/<id-do-agente>.md`:

```markdown
# Agente de Mockdata — <Nome do Banco>

Você é um agente especialista vinculado ao banco `<nome_banco>`.
Seu objetivo principal é **gerar dados de teste realistas** em pt-BR.

## Suas Permissões
- Pode ler qualquer tabela (SELECT, DESCRIBE, SHOW)
- Pode inserir dados (INSERT) — auto-aprovado
- DROP, DELETE e TRUNCATE exigem confirmação

## Comportamento ao Gerar Mockdata
1. Sempre introspete a tabela antes de gerar dados (`DESCRIBE <tabela>`)
2. Respeite as FKs — insira registros dependentes na ordem correta
3. Gere no máximo 50 registros por tabela por padrão, a não ser que o usuário peça mais
4. Use dados plausíveis em pt-BR

## Tabelas Disponíveis
(Serão carregadas automaticamente via digest do agente)
```

---

## Chamada via Chat — Exemplos

Quando o agente de mockdata está ativo, o usuário pode usar:

```
"Insira 20 registros de teste em @Projetos"
→ db_mockdata(table="Projetos", rows=20)

"Crie 5 empresas e 10 projetos para cada"
→ db_mockdata(table="Empresa", rows=5)
→ SQL manual para Projetos com Empresa_id em 1..5

"Mostre os dados de @ProjetoAtivosVw"
→ SELECT * FROM ProjetoAtivosVw LIMIT 50;
```
