"""
Schemas para guard engine e avaliação de risco de SQL.
"""
from typing import Optional
from pydantic import BaseModel


class SQLClassification(BaseModel):
    """Resultado da classificação de um SQL."""
    sql_type: str        # "SELECT" | "INSERT" | "UPDATE" | "DELETE" | "DROP" | "CREATE" | "ALTER" | "TRUNCATE" | "CALL" | "SHOW" | "DESCRIBE" | "EXPLAIN" | "OTHER"
    risk_level: str      # "low" | "medium" | "high"
    has_where: bool = True
    is_multi_statement: bool = False
    is_destructive: bool = False
    warnings: list[str] = []
    affected_objects: list[str] = []  # nomes de tabelas/views afetadas


class GuardDecision(BaseModel):
    """Decisão do guard engine para uma operação."""
    allowed: bool
    requires_confirmation: bool
    risk_level: str
    reason: str
    classification: SQLClassification
    dry_run_result: Optional[dict] = None
