"""
Serviço de Consulta Segura (Read-Only) para Target DB.
Garante que apenas SELECTs controlados sejam executados.
"""
import time
import re
from typing import Dict, Any
from sqlalchemy import text
import sqlglot
from sqlglot import exp

from app.db.session import SessionLocal
from app.services.target_db.connection_manager import connection_manager as target_db_manager
from app.services.platform.agent_database_binding_service import resolve_agent_database_binding
from app.services.observability.execution_observability_service import (
    log_agent_execution,
    generate_execution_id,
)
from app.core.logger import get_logger

logger = get_logger("target_db.query")

def validate_and_format_query(query: str) -> str:
    """
    Valida se a query é um SELECT seguro e único.
    Injeta LIMIT 100 se necessário.
    """
    # 1. Limpeza básica
    query = query.strip()
    if not query:
        raise ValueError("Query vazia.")

    # 2. Bloqueio de múltiplos statements (;)
    if ";" in query[:-1]:
        raise ValueError("Múltiplos statements (;) não são permitidos por segurança.")

    # 3. Parsing Estrutural via sqlglot
    try:
        expressions = sqlglot.parse(query, read="mysql")
        if len(expressions) > 1:
            raise ValueError("Apenas um comando SQL é permitido por vez.")
        
        expression = expressions[0]
        
        # Garante que é um SELECT
        if not isinstance(expression, exp.Select):
            raise ValueError(f"Comando '{expression.key}' não permitido. Apenas SELECT é autorizado.")

        # 4. Bloqueio de funções/cláusulas perigosas
        query_upper = query.upper()
        dangerous = ["INTO OUTFILE", "LOAD_FILE", "INFORMATION_SCHEMA", "GRANT", "REVOKE"]
        for word in dangerous:
            if word in query_upper:
                raise ValueError(f"Uso de termo proibido detectado: {word}")

        # 5. Injeção de LIMIT 100
        # Se não houver LIMIT, adicionamos. Se houver, garantimos que <= 100.
        limit_clause = expression.find(exp.Limit)
        if not limit_clause:
            query = f"{query.rstrip(';')} LIMIT 100"
        else:
            limit_val = limit_clause.expression.this
            try:
                if int(limit_val) > 100:
                    # Substitui o limite original por 100
                    query = re.sub(r"(?i)LIMIT\s+\d+", "LIMIT 100", query)
            except (ValueError, TypeError):
                pass
                
        return query

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        logger.error(f"Erro no parser SQL: {str(e)}")
        raise ValueError(f"Query SQL inválida ou malformada: {str(e)}")


def _enforce_access_mode(access_mode: str, query: str) -> None:
    """
    Respeita access_mode do binding.

    Nesta etapa, mesmo `readwrite` continua bloqueando escrita por segurança.
    """
    mode = (access_mode or "readonly").lower()

    # A validação estrutural já garante SELECT-only, mas mantemos esta guarda explícita.
    query_upper = query.strip().upper()
    blocked = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ", "CREATE ")
    if any(token in query_upper for token in blocked):
        raise ValueError("Comandos DDL/DML não são permitidos neste endpoint")

    if mode == "readonly":
        return
    if mode == "readwrite":
        # Readwrite existe no binding para evolução futura, mas escrita segue bloqueada nesta etapa.
        return

    raise ValueError(f"access_mode inválido no binding: '{access_mode}'")


def execute_read_query(
    agent_id: str,
    raw_query: str,
    database_connection_id: int | None = None,
    execution_id: str | None = None,
) -> Dict[str, Any]:
    """
    Executa uma consulta SELECT segura no target_db.
    """
    execution_id = execution_id or generate_execution_id()
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        # 1. Validar e Sanitizar
        safe_query = validate_and_format_query(raw_query)

        resolved_binding = resolve_agent_database_binding(
            db,
            agent_id,
            database_connection_id=database_connection_id,
        )
        _enforce_access_mode(resolved_binding.get("access_mode", "readonly"), safe_query)

        engine = target_db_manager.get_engine(
            db,
            agent_id,
            database_connection_id=resolved_binding.get("database_connection_id"),
        )
        
        # 2. Executar com Timeout
        with engine.connect() as conn:
            # Seta timeout na sessão (MySQL específico)
            conn.execute(text("SET max_execution_time=5000")) 
            
            result = conn.execute(text(safe_query))
            
            # 3. Processar Resultados
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(100)]
            
            execution_time = (time.time() - start_time) * 1000

            log_agent_execution(
                db,
                execution_id=execution_id,
                agent_id=agent_id,
                database_connection_id=resolved_binding.get("database_connection_id"),
                query=safe_query,
                status="success",
                execution_time_ms=execution_time,
                result_summary={
                    "row_count": len(rows),
                    "column_count": len(columns),
                },
            )
            
            logger.info(
                "Query executada | execution_id=%s | agent=%s | db_connection_id=%s | rows=%s | time_ms=%s",
                execution_id,
                agent_id,
                resolved_binding.get("database_connection_id"),
                len(rows),
                round(execution_time, 2),
            )
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": round(execution_time, 2),
                "safe_query": safe_query # Retorna a query com o LIMIT injetado para auditoria
            }
            
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        try:
            db_conn_id = None
            if "resolved_binding" in locals() and isinstance(resolved_binding, dict):
                db_conn_id = resolved_binding.get("database_connection_id")
            query_for_log = raw_query
            if "safe_query" in locals() and isinstance(safe_query, str):
                query_for_log = safe_query
            log_agent_execution(
                db,
                execution_id=execution_id,
                agent_id=agent_id,
                database_connection_id=db_conn_id,
                query=query_for_log,
                status="error",
                execution_time_ms=execution_time,
                error_message=str(e),
                result_summary={},
            )
        except Exception:
            # Nunca deixa de propagar o erro original por falha de log
            pass

        logger.error(
            "Erro na execução da query | execution_id=%s | agent=%s | error=%s",
            execution_id,
            agent_id,
            str(e),
        )
        raise
    finally:
        db.close()
