"""
db_introspection: Tool para introspectão de schema MySQL.
Conecta diretamente ao banco — bypass do guard engine de permissões,
pois introspectão é uma operação de sistema, não de usuário.
"""
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.execution import DBExecuteRequest, DBExecuteResult
from app.tools import db_connection_manager

logger = get_logger("db_introspection")


def _run_direct(agent: AgentConfig, sql: str, params: dict | None = None) -> DBExecuteResult:
    """
    Executa SQL diretamente no banco do agente, sem passar pelo guard engine.
    Usado exclusivamente para operações de introspectão de schema (sistema).
    """
    if not agent.database:
        return DBExecuteResult(success=False, error="Agente não possui banco de dados configurado")
    try:
        import time
        conn = db_connection_manager.get_connection(agent.id, agent.database)
        start = time.time()
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = []
        columns = []
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
        cursor.close()
        elapsed = (time.time() - start) * 1000
        return DBExecuteResult(success=True, rows=rows, columns=columns, execution_time_ms=round(elapsed, 2))
    except Exception as e:
        logger.error(f"[INTROSPECT] Erro direto ao executar SQL: {e} | sql={sql[:120]}")
        return DBExecuteResult(success=False, error=str(e))


def list_tables(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as tabelas do banco via INFORMATION_SCHEMA (mais confiável)."""
    sql = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """
    res = _run_direct(agent, sql)
    if res.success:
        logger.debug(f"list_tables: {len(res.rows)} tabelas encontradas")
    return res


def list_views(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as views do banco via INFORMATION_SCHEMA."""
    sql = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_TYPE = 'VIEW'
        ORDER BY TABLE_NAME
    """
    res = _run_direct(agent, sql)
    if res.success:
        logger.debug(f"list_views: {len(res.rows)} views encontradas")
    return res


def list_triggers(agent: AgentConfig) -> DBExecuteResult:
    """Lista todos os triggers do banco."""
    return _run_direct(agent, "SHOW TRIGGERS")


def list_procedures(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as procedures do banco."""
    return _run_direct(agent, "SHOW PROCEDURE STATUS WHERE Db = DATABASE()")


def list_functions(agent: AgentConfig) -> DBExecuteResult:
    """Lista todas as functions do banco."""
    return _run_direct(agent, "SHOW FUNCTION STATUS WHERE Db = DATABASE()")


def describe_table(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Descreve a estrutura de uma tabela."""
    return _run_direct(agent, f"DESCRIBE `{_safe_name(table_name)}`")


def show_create_table(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Retorna o DDL completo de uma tabela."""
    return _run_direct(agent, f"SHOW CREATE TABLE `{_safe_name(table_name)}`")


def show_create_view(agent: AgentConfig, view_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma view."""
    return _run_direct(agent, f"SHOW CREATE VIEW `{_safe_name(view_name)}`")


def show_create_trigger(agent: AgentConfig, trigger_name: str) -> DBExecuteResult:
    """Retorna o DDL de um trigger."""
    return _run_direct(agent, f"SHOW CREATE TRIGGER `{_safe_name(trigger_name)}`")


def show_create_procedure(agent: AgentConfig, proc_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma procedure."""
    return _run_direct(agent, f"SHOW CREATE PROCEDURE `{_safe_name(proc_name)}`")


def show_create_function(agent: AgentConfig, func_name: str) -> DBExecuteResult:
    """Retorna o DDL de uma function."""
    return _run_direct(agent, f"SHOW CREATE FUNCTION `{_safe_name(func_name)}`")


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
    return _run_direct(agent, sql, params={"table_name": table_name})


def get_indexes(agent: AgentConfig, table_name: str) -> DBExecuteResult:
    """Obtém índices de uma tabela."""
    return _run_direct(agent, f"SHOW INDEX FROM `{_safe_name(table_name)}`")


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
    return _run_direct(agent, sql, params={"table_name": table_name})


def get_database_info(agent: AgentConfig) -> DBExecuteResult:
    """Informações gerais do banco (versão, charset, etc.)."""
    sql = """
        SELECT 
            DATABASE() AS current_db,
            VERSION() AS mysql_version,
            @@character_set_database AS charset,
            @@collation_database AS collation
    """
    return _run_direct(agent, sql)


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
