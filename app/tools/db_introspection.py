"""
db_introspection: Tool para introspecção de schema MySQL.
Consulta estrutura real do banco sem assumir nada.
"""
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.execution import DBExecuteRequest, DBExecuteResult
from app.tools import db_execute as executor

logger = get_logger("db_introspection")


def list_tables(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as tabelas do banco."""
    return executor.execute(
        DBExecuteRequest(sql="SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'", mode="read"),
        agent,
    )


def list_views(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as views do banco."""
    return executor.execute(
        DBExecuteRequest(sql="SHOW FULL TABLES WHERE Table_type = 'VIEW'", mode="read"),
        agent,
    )


def list_triggers(agent: AgentConfig) -> DBExecuteResult:
    """Lista todos os triggers do banco."""
    return executor.execute(
        DBExecuteRequest(sql="SHOW TRIGGERS", mode="read"),
        agent,
    )


def list_procedures(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as procedures do banco."""
    sql = "SHOW PROCEDURE STATUS WHERE Db = DATABASE()"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def list_functions(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as functions do banco."""
    sql = "SHOW FUNCTION STATUS WHERE Db = DATABASE()"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def describe_table(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Descreve a estrutura de uma tabela."""
    sql = f"DESCRIBE `{_safe_name(table_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def show_create_table(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Retorna o DDL completo de uma tabela."""
    sql = f"SHOW CREATE TABLE `{_safe_name(table_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def show_create_view(agent: AgentConfig, view_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma view."""
    sql = f"SHOW CREATE VIEW `{_safe_name(view_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def show_create_trigger(agent: AgentConfig, trigger_name: str) -> DBExecuteResult:
    """Retorna o DDL de um trigger."""
    sql = f"SHOW CREATE TRIGGER `{_safe_name(trigger_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def show_create_procedure(agent: AgentConfig, proc_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma procedure."""
    sql = f"SHOW CREATE PROCEDURE `{_safe_name(proc_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def show_create_function(agent: AgentConfig, func_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma function."""
    sql = f"SHOW CREATE FUNCTION `{_safe_name(func_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def get_columns(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Obtém colunas detalhadas via INFORMATION_SCHEMA."""
    sql = """
        SELECT 
            COLUMN_NAME,
            ORDINAL_POSITION,
            COLUMN_DEFAULT,
            IS_NULLABLE,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            COLUMN_TYPE,
            COLUMN_KEY,
            EXTRA,
            COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %(table_name)s
        ORDER BY ORDINAL_POSITION
    """
    return executor.execute(
        DBExecuteRequest(sql=sql, params={"table_name": table_name}, mode="read"),
        agent,
    )


def get_indexes(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Obtém índices de uma tabela."""
    sql = f"SHOW INDEX FROM `{_safe_name(table_name)}`"
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def get_foreign_keys(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Obtém foreign keys de uma tabela."""
    sql = """
        SELECT
            CONSTRAINT_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %(table_name)s
          AND REFERENCED_TABLE_NAME IS NOT NULL
    """
    return executor.execute(
        DBExecuteRequest(sql=sql, params={"table_name": table_name}, mode="read"),
        agent,
    )


def get_database_info(agent: AgentConfig) -> DBExecuteResult:
    """Informações gerais do banco (versão, charset, etc.)."""
    sql = """
        SELECT 
            DATABASE() AS current_db,
            VERSION() AS mysql_version,
            @@character_set_database AS charset,
            @@collation_database AS collation
    """
    return executor.execute(DBExecuteRequest(sql=sql, mode="read"), agent)


def introspect(agent: AgentConfig, action: str, target: Optional[str] = None) -> DBExecuteResult:
    """
    Interface unificada de introspecção.
    
    Args:
        agent: Configuração do agente.
        action: Ação a executar (list_tables, describe_table, show_create_table, etc.)
        target: Nome do objeto alvo (tabela, view, etc.) quando aplicável.
    """
    # Normalizar action: aceitar aliases em português e variantes sem underscore
    _ALIASES: dict[str, str] = {
        "listar tabelas":     "list_tables",
        "listar views":       "list_views",
        "listar triggers":    "list_triggers",
        "listar procedimentos": "list_procedures",
        "listar funções":     "list_functions",
        "listar funcoes":     "list_functions",
        "descrever tabela":   "describe_table",
        "mostrar tabela":     "show_create_table",
        "mostrar view":       "show_create_view",
        "mostrar trigger":    "show_create_trigger",
        "mostrar procedimento": "show_create_procedure",
        "informações do banco": "get_database_info",
        "info banco":         "get_database_info",
        # sem underscore
        "list tables":        "list_tables",
        "list views":         "list_views",
        "list triggers":      "list_triggers",
        "list procedures":    "list_procedures",
        "list functions":     "list_functions",
        "describe table":     "describe_table",
        "show create table":  "show_create_table",
        "get database info":  "get_database_info",
    }
    normalized = _ALIASES.get(action.lower().strip(), action)
    if normalized != action:
        logger.debug(f"Action alias resolvido: '{action}' → '{normalized}'")
    action = normalized

    action_map = {
        "list_tables": lambda: list_tables(agent),
        "list_views": lambda: list_views(agent),
        "list_triggers": lambda: list_triggers(agent),
        "list_procedures": lambda: list_procedures(agent),
        "list_functions": lambda: list_functions(agent),
        "describe_table": lambda: describe_table(agent, target) if target else _error("target obrigatório"),
        "show_create_table": lambda: show_create_table(agent, target) if target else _error("target obrigatório"),
        "show_create_view": lambda: show_create_view(agent, target) if target else _error("target obrigatório"),
        "show_create_trigger": lambda: show_create_trigger(agent, target) if target else _error("target obrigatório"),
        "show_create_procedure": lambda: show_create_procedure(agent, target) if target else _error("target obrigatório"),
        "show_create_function": lambda: show_create_function(agent, target) if target else _error("target obrigatório"),
        "get_columns": lambda: get_columns(agent, target) if target else _error("target obrigatório"),
        "get_indexes": lambda: get_indexes(agent, target) if target else _error("target obrigatório"),
        "get_foreign_keys": lambda: get_foreign_keys(agent, target) if target else _error("target obrigatório"),
        "get_database_info": lambda: get_database_info(agent),
    }

    fn = action_map.get(action)
    if fn is None:
        logger.warning(f"Ação de introspecção desconhecida: '{action}' | disponíveis: {list(action_map.keys())}")
        return _error(f"Ação de introspecção desconhecida: {action}")

    return fn()



def _safe_name(name: str) -> str:
    """Sanitiza nome de tabela/objeto removendo backticks e chars perigosos."""
    return name.replace("`", "").replace(";", "").strip()


def _error(msg: str) -> DBExecuteResult:
    """Retorna um resultado de erro."""
    return DBExecuteResult(success=False, error=msg)
