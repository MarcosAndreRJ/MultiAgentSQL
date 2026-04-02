"""
Schemas para execução SQL e resultados.
"""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class DBExecuteRequest(BaseModel):
    """Payload para executar SQL via db_execute."""
    sql: str
    params: dict = Field(default_factory=dict)
    mode: str = "read"  # "read" | "write" | "ddl"
    dry_run: bool = False


class DBExecuteResult(BaseModel):
    """Resultado de uma execução SQL."""
    success: bool
    rows: list[dict] = Field(default_factory=list)
    rows_affected: int = 0
    columns: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    sql_executed: Optional[str] = None
    error: Optional[str] = None
    truncated: bool = False  # True se resultado foi truncado por max_rows


class ExecutionRecord(BaseModel):
    """Registro de uma execução para histórico/auditoria."""
    id: str
    agent_id: str
    session_id: str
    database: Optional[str] = None
    sql: str
    mode: str
    success: bool
    rows_affected: int = 0
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    risk_level: str = "low"
    confirmed_by_user: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionHistory(BaseModel):
    """Lista de execuções recentes."""
    agent_id: str
    records: list[ExecutionRecord] = Field(default_factory=list)
    total: int = 0
