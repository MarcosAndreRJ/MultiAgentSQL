# MySQL Defaults Skill
# Heurísticas genéricas de operação MySQL para agentes especialistas.

## Objetivo
Fornecer regras base de operação MySQL segura, sem assumir regras de negócio específicas.

## Regras de Operação

### Consulta Antes de Afirmar
- Antes de afirmar que uma tabela existe, consulte via SHOW TABLES ou INFORMATION_SCHEMA
- Antes de afirmar que uma coluna existe, use DESCRIBE ou INFORMATION_SCHEMA.COLUMNS
- Antes de qualquer DDL relevante, verifique o estado atual do objeto

### Ordem de Prioridade para Confirmação
- DELETE → sempre confirmar
- DROP → sempre confirmar  
- TRUNCATE → sempre confirmar
- UPDATE sem WHERE → sempre confirmar
- ALTER TABLE com DROP COLUMN → confirmar

### Leitura Segura
- Para exploração inicial, SELECT * é aceitável
- Para operações estruturadas, prefira colunas explícitas
- Sempre use LIMIT em queries exploratórias desconhecidas (ex: LIMIT 100)

### Escrita Segura
- Todo UPDATE deve ter WHERE
- Todo DELETE deve ter WHERE
- Sem WHERE = risco alto = exige confirmação

## Padrões de Introspecção Recomendados

```sql
-- Listar tabelas
SHOW TABLES;

-- Estrutura de tabela
DESCRIBE nome_tabela;

-- DDL completo
SHOW CREATE TABLE nome_tabela;

-- Colunas via INFORMATION_SCHEMA
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'nome_tabela';

-- Views
SHOW FULL TABLES WHERE Table_type = 'VIEW';

-- Triggers
SHOW TRIGGERS;

-- Procedures e Functions
SHOW PROCEDURE STATUS WHERE Db = DATABASE();
SHOW FUNCTION STATUS WHERE Db = DATABASE();

-- Versão do MySQL
SELECT VERSION();
```

## Proibições
- Não assumir schema por nome de tabela
- Não assumir PK como `id`
- Não assumir soft delete (`deleted_at` ou `is_deleted`)
- Não afirmar sucesso sem retorno real do backend

## Observações
- MySQL e MariaDB têm comportamentos diferentes em alguns recursos avançados
- Evitar introspecção repetitiva no mesmo turno se o schema já foi consultado
- Em caso de dúvida estrutural, consultar sempre
