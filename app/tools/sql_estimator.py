"""
sql_estimator: Estimativas simples sobre impacto de SQL.
Usa INFORMATION_SCHEMA para estimar linhas afetadas quando possível.
"""
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.execution import DBExecuteRequest, DBExecuteResult
from app.tools import db_execute as executor

logger = get_logger("sql_estimator")


def estimate_row_count(agent: AgentConfig, table_name: str) -> Optional[int]:
    """
    Estima número de linhas de uma tabela via INFORMATION_SCHEMA.
    A estimativa pode ser aproximada para tabelas grandes.
    
    Returns:
        Contagem estimada ou None em caso de erro.
    """
    sql = """
        SELECT TABLE_ROWS
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
    """
    result = executor.execute(
        DBExecuteRequest(sql=sql, params={"1": table_name}, mode="read"),
        agent,
    )
    
    if result.success and result.rows:
        return result.rows[0].get("TABLE_ROWS")
    return None


def explain_query(agent: AgentConfig, sql: str) -> DBExecuteResult:
    """
    Executa EXPLAIN para analisar plano de execução de uma query.
    
    Args:
        agent: Agente com acesso ao banco.
        sql: SQL SELECT a analisar.
        
    Returns:
        Resultado do EXPLAIN.
    """
    explain_sql = f"EXPLAIN {sql}"
    return executor.execute(
        DBExecuteRequest(sql=explain_sql, mode="read"),
        agent,
    )


def count_affected(agent: AgentConfig, sql: str) -> Optional[int]:
    """
    Tenta estimar quantas linhas serão afetadas por um UPDATE/DELETE.
    Converte UPDATE/DELETE em SELECT COUNT(*) com mesma cláusula WHERE.
    
    Returns:
        Contagem real ou None se não for possível estimar.
    """
    import re
    
    sql_stripped = sql.strip()
    
    # DELETE: DELETE FROM tabela WHERE cond → SELECT COUNT(*) FROM tabela WHERE cond
    delete_match = re.match(
        r"DELETE\s+FROM\s+(`?\w+`?)\s*(WHERE\s+.+)?",
        sql_stripped,
        re.IGNORECASE | re.DOTALL,
    )
    if delete_match:
        table = delete_match.group(1)
        where = delete_match.group(2) or ""
        count_sql = f"SELECT COUNT(*) as affected FROM {table} {where}"
        result = executor.execute(
            DBExecuteRequest(sql=count_sql, mode="read"),
            agent,
        )
        if result.success and result.rows:
            return result.rows[0].get("affected")
        return None

    # UPDATE: mais complexo, apenas tentativa simplificada
    update_match = re.match(
        r"UPDATE\s+(`?\w+`?)\s+SET\s+.+?\s+(WHERE\s+.+)?",
        sql_stripped,
        re.IGNORECASE | re.DOTALL,
    )
    if update_match:
        table = update_match.group(1)
        where = update_match.group(2) or ""
        count_sql = f"SELECT COUNT(*) as affected FROM {table} {where}"
        result = executor.execute(
            DBExecuteRequest(sql=count_sql, mode="read"),
            agent,
        )
        if result.success and result.rows:
            return result.rows[0].get("affected")
        return None

    return None
