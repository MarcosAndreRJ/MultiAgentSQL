"""
db_execute: Tool principal para execução de SQL.
Executa SQL diretamente no banco sem modificar ou decidir risco.
A decisão de risco é do guard_engine — essa tool apenas executa.
"""
import time
from typing import Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.agent import AgentConfig
from app.schemas.execution import DBExecuteRequest, DBExecuteResult
from app.tools.db_connection_manager import get_connection
from app.services.observability.execution_observability_service import log_agent_execution
from app.db.session import SessionLocal

logger = get_logger("db_execute")


def execute(
    request: DBExecuteRequest,
    agent: AgentConfig,
) -> DBExecuteResult:
    """
    Executa SQL no banco associado ao agente.
    
    Esta tool:
    - NÃO modifica o SQL
    - NÃO decide sobre risco
    - Executa exatamente o SQL recebido
    - Retorna o resultado real
    
    Args:
        request: Payload com SQL, params e configurações.
        agent: Configuração do agente (e seu banco de dados).
        
    Returns:
        DBExecuteResult com resultado real ou erro.
    """
    if not agent.database:
        return DBExecuteResult(
            success=False,
            error="Agente não possui banco de dados configurado",
        )

    if not request.sql or not request.sql.strip():
        return DBExecuteResult(
            success=False,
            error="SQL vazio",
        )

    sql = request.sql.strip()

    # Dry run: apenas retorna sem executar
    if request.dry_run:
        logger.info(f"DRY RUN | agente={agent.id} | sql={sql[:100]}")
        return DBExecuteResult(
            success=True,
            sql_executed=sql,
            rows=[],
            rows_affected=0,
        )

    start_time = time.time()

    try:
        conn = get_connection(agent.id, agent.database)
        return _run_sql(conn, sql, request.params or {}, agent, execution_id=request.execution_id)

    except MySQLError as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"Erro MySQL | agente={agent.id} | erro={e} | sql={sql[:200]}")
        return DBExecuteResult(
            success=False,
            error=str(e),
            execution_time_ms=elapsed,
            sql_executed=sql,
        )
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"Erro inesperado | agente={agent.id} | erro={e}")
        return DBExecuteResult(
            success=False,
            error=f"Erro interno: {str(e)}",
            execution_time_ms=elapsed,
            sql_executed=sql,
        )


def _run_sql(
    conn: mysql.connector.MySQLConnection,
    sql: str,
    params: dict,
    agent: AgentConfig,
    execution_id: Optional[str] = None,
) -> DBExecuteResult:
    """Executa o SQL na conexão e retorna resultado formatado."""
    start_time = time.time()
    max_rows = agent.behavior.max_result_rows or settings.DB_MAX_RESULT_ROWS

    cursor = None
    try:
        # Criar cursor com dictionary para retorno de dicts
        cursor = conn.cursor(dictionary=True)

        # Executar SQL
        # Suporte a multi-statement via multi=True apenas se necessário
        # Detectar multi-statement de forma simples
        sql_stripped = sql.strip().rstrip(";")
        
        # Para statements simples, execução direta
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = []
        columns = []
        rows_affected = 0
        truncated = False

        # Verificar se há resultados (SELECT, SHOW, DESCRIBE, EXPLAIN)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            fetched = cursor.fetchmany(max_rows + 1)
            
            if len(fetched) > max_rows:
                rows = fetched[:max_rows]
                truncated = True
                logger.warning(f"Resultado truncado: máximo {max_rows} linhas | agente={agent.id}")
            else:
                rows = fetched
        else:
            # DML/DDL: capturar rows affected
            rows_affected = cursor.rowcount if cursor.rowcount != -1 else 0

        elapsed = (time.time() - start_time) * 1000

        logger.info(
            f"SQL executado | agente={agent.id} | rows={len(rows)} | affected={rows_affected} | {elapsed:.1f}ms"
        )

        exec_result = DBExecuteResult(
            success=True,
            rows=rows,
            rows_affected=rows_affected,
            columns=columns,
            execution_time_ms=round(elapsed, 2),
            sql_executed=sql,
            truncated=truncated,
        )

        # Log de Observabilidade
        if execution_id:
            try:
                with SessionLocal() as db:
                    log_agent_execution(
                        db=db,
                        execution_id=execution_id,
                        agent_id=agent.id,
                        database_connection_id=None, # Ver nota abaixo
                        query=sql,
                        status="success",
                        execution_time_ms=elapsed,
                        result_summary={
                            "row_count": len(rows),
                            "rows_affected": rows_affected,
                            "column_count": len(columns),
                            "truncated": truncated
                        }
                    )
            except Exception as e:
                logger.warning(f"Erro ao registrar log de observabilidade: {e}")

        return exec_result

    except MySQLError as e:
        # Log de erro de execução
        if execution_id:
            try:
                elapsed = (time.time() - start_time) * 1000
                with SessionLocal() as db:
                    log_agent_execution(
                        db=db,
                        execution_id=execution_id,
                        agent_id=agent.id,
                        database_connection_id=None,
                        query=sql,
                        status="error",
                        execution_time_ms=elapsed,
                        error_message=str(e),
                        result_summary={}
                    )
            except Exception:
                pass
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass


def execute_multi(sqls: list[str], agent: AgentConfig) -> list[DBExecuteResult]:
    """
    Executa múltiplos SQLs em sequência.
    Para suporte a procedures/triggers com DELIMITER.
    """
    results = []
    for sql in sqls:
        req = DBExecuteRequest(sql=sql, mode="ddl")
        result = execute(req, agent)
        results.append(result)
        if not result.success:
            logger.warning(f"Multi-execute parou no SQL: {sql[:100]}")
            break
    return results
