# DDL Rules Skill
# Boas práticas para operações de DDL (CREATE, ALTER, DROP) em MySQL.

## Objetivo
Orientar o agente a gerar DDL seguro, consistente e compatível com MySQL/MariaDB.

## Regras DDL

### Criação de Tabelas
- Sempre usar ENGINE=InnoDB (padrão mais seguro)
- Sempre usar DEFAULT CHARSET=utf8mb4
- Sempre definir PRIMARY KEY
- Usar AUTO_INCREMENT para PKs numéricas
- Preferir NOT NULL com DEFAULT quando possível
- Usar comentários nas colunas quando útil

### Alteração de Tabelas
- Antes de ALTER TABLE, verificar a estrutura atual com DESCRIBE ou SHOW CREATE TABLE
- ALTER com DROP COLUMN é destrutivo → exige confirmação
- ALTER com MODIFY pode alterar dados → verificar impacto
- Adicionar colunas sem NOT NULL sem DEFAULT pode ser problemático em tabelas populadas

### Exclusão de Objetos
- DROP TABLE é irreversível → sempre confirmar
- DROP VIEW → confirmar
- DROP TRIGGER → confirmar
- DROP PROCEDURE / FUNCTION → confirmar

### Índices
- Verificar índices existentes antes de criar (evitar duplicatas)
- Índices em colunas de JOIN e WHERE frequentes melhoram performance
- Índices desnecessários prejudicam escrita

### Views
- Verificar se view já existe antes de CREATE VIEW
- Usar CREATE OR REPLACE VIEW quando atualizar
- Views complexas podem ter impacto em performance

### Triggers
- Verificar se trigger já existe antes de criar
- DELIMITER deve ser definido antes de triggers multi-statement
- DROP TRIGGER IF EXISTS antes de recriar é prática segura

### Procedures e Functions
- Verificar existência antes de criar
- DROP PROCEDURE IF EXISTS / DROP FUNCTION IF EXISTS antes de recriar
- Usar DELIMITER $$ para separar SQL do corpo

## Exemplos

### Criar tabela corretamente
```sql
CREATE TABLE usuario (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL,
  dt_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dt_atualizacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_ativo TINYINT(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uk_usuario_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tabela de usuários';
```

### Criar trigger corretamente
```sql
DELIMITER $$

DROP TRIGGER IF EXISTS trg_usuario_after_insert $$

CREATE TRIGGER trg_usuario_after_insert
AFTER INSERT ON usuario
FOR EACH ROW
BEGIN
  -- lógica aqui
END $$

DELIMITER ;
```

## Proibições
- Não criar tabela sem PRIMARY KEY
- Não usar ENGINE=MyISAM
- Não usar charset latin1
- Não executar DROP sem confirmação
- Não alterar coluna sem verificar dados existentes
