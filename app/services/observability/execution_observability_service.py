"""
Serviços de observabilidade para execuções reais.

Inclui:
- logs de execução SQL por agente
- logs de chamadas de provider
- métricas agregadas por agente
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.db import models as db_models

logger = get_logger("observability.execution")

_MAX_QUERY_LOG_LEN = 2000
_MAX_ERROR_LOG_LEN = 500


def generate_execution_id() -> str:
    return f"exec_{uuid.uuid4().hex}"


def sanitize_query(query: str) -> str:
    """
    Sanitiza query para persistência em log:
    - remove/mascara literais comuns (strings, números)
    - remove comentários SQL
    - normaliza whitespace
    - trunca tamanho
    """
    if not query:
        return ""

    # 1. Remover comentários de linha e bloco
    value = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    
    value = value.strip()
    
    # 2. Mascarar strings (entre aspas simples ou duplas)
    value = re.sub(r"'[^']*'", "'?'", value)
    value = re.sub(r'"[^"]*"', '"?"', value)
    
    # 3. Mascarar números (que não sejam parte de identificadores)
    # Ex: WHERE id = 123 -> WHERE id = ?
    value = re.sub(r"(?<=\s|=|>|<|!)\d+(?=\s|;|$|,|\))", "?", value)
    
    # 4. Normalizar whitespace
    value = re.sub(r"\s+", " ", value)
    
    return value.strip()[:_MAX_QUERY_LOG_LEN]


def sanitize_error_message(error_message: str) -> str:
    if not error_message:
        return ""
    value = error_message.strip()
    # mascara padrão user:pass@ em URIs
    value = re.sub(r"//[^:/\s]+:[^@/\s]+@", "//***:***@", value)
    return value[:_MAX_ERROR_LOG_LEN]


def log_agent_execution(
    db: Session,
    *,
    execution_id: str,
    agent_id: str,
    database_connection_id: int | None,
    query: str,
    status: str,
    execution_time_ms: float,
    error_message: str | None = None,
    provider_id: int | None = None,
    model_id: int | None = None,
    result_summary: Dict[str, Any] | None = None,
) -> None:
    """Persiste log de execução SQL de agente."""
    try:
        row = db_models.AgentExecutionLog(
            execution_id=execution_id,
            agent_id=agent_id,
            provider_id=provider_id,
            model_id=model_id,
            database_connection_id=database_connection_id,
            query=sanitize_query(query),
            status=status,
            execution_time_ms=int(round(execution_time_ms or 0)),
            error_message=sanitize_error_message(error_message or "") or None,
            result_summary_json=json.dumps(result_summary or {}),
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Falha ao persistir agent_execution_log | execution_id=%s | error=%s", execution_id, exc)


def log_provider_execution(
    db: Session,
    *,
    execution_id: str,
    provider_id: int | None,
    model_id: int | None,
    operation: str,
    status: str,
    latency_ms: float,
    error_message: str | None = None,
) -> None:
    """Persiste log de execução/chamada de provider."""
    try:
        row = db_models.ProviderExecutionLog(
            execution_id=execution_id,
            provider_id=provider_id,
            model_id=model_id,
            operation=operation,
            status=status,
            latency_ms=int(round(latency_ms or 0)),
            error_message=sanitize_error_message(error_message or "") or None,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Falha ao persistir provider_execution_log | execution_id=%s | error=%s", execution_id, exc)


def list_agent_observability_metrics(db: Session) -> List[Dict[str, Any]]:
    """Retorna métricas agregadas por agent_id."""
    success_case = case((db_models.AgentExecutionLog.status == "success", 1), else_=0)

    rows = (
        db.query(
            db_models.AgentExecutionLog.agent_id.label("agent_id"),
            func.count(db_models.AgentExecutionLog.id).label("total_executions"),
            func.sum(success_case).label("total_success"),
            func.avg(db_models.AgentExecutionLog.execution_time_ms).label("avg_latency_ms"),
            func.max(db_models.AgentExecutionLog.created_at).label("last_execution_at"),
        )
        .group_by(db_models.AgentExecutionLog.agent_id)
        .all()
    )

    result: List[Dict[str, Any]] = []
    for row in rows:
        total = int(row.total_executions or 0)
        total_success = int(row.total_success or 0)
        success_rate = (float(total_success) / float(total)) if total > 0 else 0.0
        result.append(
            {
                "agent_id": row.agent_id,
                "total_executions": total,
                "success_rate": round(success_rate, 4),
                "avg_latency_ms": float(round(row.avg_latency_ms or 0, 2)),
                "last_execution_at": row.last_execution_at,
            }
        )

    return result


def list_agent_execution_logs(db: Session, agent_id: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Lista logs de execução por agente com paginação simples."""
    page = max(page, 1)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    base_query = db.query(db_models.AgentExecutionLog).filter(db_models.AgentExecutionLog.agent_id == agent_id)
    total = base_query.count()
    rows = (
        base_query.order_by(db_models.AgentExecutionLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "agent_id": agent_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "id": r.id,
                "execution_id": r.execution_id,
                "provider_id": r.provider_id,
                "model_id": r.model_id,
                "database_connection_id": r.database_connection_id,
                "query": r.query,
                "status": r.status,
                "execution_time_ms": r.execution_time_ms,
                "error_message": r.error_message,
                "result_summary": json.loads(r.result_summary_json) if r.result_summary_json else {},
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


def cleanup_old_logs(db: Session, days: int = 7) -> Dict[str, int]:
    """
    Remove logs de execução mais antigos que o período especificado.
    Retorna contagem de registros removidos por tabela.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    counts = {}

    try:
        # 1. Agent Execution Logs
        deleted_agent_logs = db.query(db_models.AgentExecutionLog).filter(
            db_models.AgentExecutionLog.created_at < cutoff
        ).delete()
        counts["agent_execution_logs"] = deleted_agent_logs

        # 2. Provider Execution Logs
        deleted_provider_logs = db.query(db_models.ProviderExecutionLog).filter(
            db_models.ProviderExecutionLog.created_at < cutoff
        ).delete()
        counts["provider_execution_logs"] = deleted_provider_logs

        # 3. Health Check Logs
        deleted_health_logs = db.query(db_models.HealthCheckLog).filter(
            db_models.HealthCheckLog.checked_at < cutoff
        ).delete()
        counts["health_check_logs"] = deleted_health_logs

        db.commit()
        logger.info(
            "Cleanup de logs concluído | cutoff=%s | removidos=%s",
            cutoff.isoformat(),
            counts
        )
        return counts
    except Exception as exc:
        db.rollback()
        logger.error("Falha ao executar cleanup de logs | error=%s", exc)
        return {"error": 1}
