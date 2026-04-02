"""
Execution Service: execução direta de SQL via API (fora do agent loop).
Usado para endpoints de execução direta para testes e CLI.
"""
import uuid
from datetime import datetime
from typing import Optional

from app.core import agent_registry
from app.core.guard_engine import evaluate as guard_evaluate
from app.core.logger import get_logger
from app.core.sql_classifier import classify_sql
from app.schemas.execution import DBExecuteRequest, DBExecuteResult, ExecutionRecord
from app.tools import db_execute

logger = get_logger("execution_service")

# Histórico de execuções em memória
_history: list[ExecutionRecord] = []
MAX_HISTORY = 200


async def execute_sql(
    agent_id: str,
    sql: str,
    session_id: str,
    skip_guard: bool = False,
) -> dict:
    """
    Executa SQL diretamente para um agente (via API de execução).
    Aplica guard antes de executar.
    
    Returns:
        Dict com success, result, guard_decision, classification.
    """
    config = agent_registry.get(agent_id)
    if not config:
        return {"success": False, "error": f"Agente '{agent_id}' não encontrado"}

    if not config.database:
        return {"success": False, "error": "Agente não possui banco de dados configurado"}

    # Classificar SQL
    classification = classify_sql(sql)

    # Guard
    if not skip_guard:
        guard_decision = guard_evaluate(sql, config)
        if not guard_decision.allowed:
            return {
                "success": False,
                "error": f"Bloqueado: {guard_decision.reason}",
                "classification": classification.model_dump(),
                "guard_decision": guard_decision.model_dump(),
            }
        if guard_decision.requires_confirmation:
            return {
                "success": False,
                "requires_confirmation": True,
                "error": f"Confirmação necessária: {guard_decision.reason}",
                "classification": classification.model_dump(),
                "guard_decision": guard_decision.model_dump(),
            }

    # Executar
    req = DBExecuteRequest(
        sql=sql,
        mode=_sql_type_to_mode(classification.sql_type),
    )
    result = db_execute.execute(req, config)

    # Registrar no histórico
    _record_execution(agent_id, session_id, sql, classification, result)

    return {
        "success": result.success,
        "result": result.model_dump(),
        "classification": classification.model_dump(),
    }


def get_execution_history(agent_id: Optional[str] = None, limit: int = 50) -> list[ExecutionRecord]:
    """Retorna histórico de execuções."""
    if agent_id:
        filtered = [r for r in _history if r.agent_id == agent_id]
    else:
        filtered = list(_history)
    return filtered[-limit:]


def _record_execution(agent_id, session_id, sql, classification, result) -> None:
    """Registra execução no histórico."""
    record = ExecutionRecord(
        id=f"exec_{uuid.uuid4().hex[:10]}",
        agent_id=agent_id,
        session_id=session_id,
        sql=sql,
        mode=_sql_type_to_mode(classification.sql_type),
        success=result.success,
        rows_affected=result.rows_affected,
        error=result.error,
        execution_time_ms=result.execution_time_ms,
        risk_level=classification.risk_level,
    )
    _history.append(record)
    if len(_history) > MAX_HISTORY:
        _history.pop(0)


def _sql_type_to_mode(sql_type: str) -> str:
    read_types = {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"}
    ddl_types = {"CREATE", "ALTER", "DROP", "TRUNCATE"}
    if sql_type in read_types:
        return "read"
    elif sql_type in ddl_types:
        return "ddl"
    return "write"
