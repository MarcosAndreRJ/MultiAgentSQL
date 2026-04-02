from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PatternFilter(BaseModel):
    """Representa um filtro abstrato em um padrão semântico."""
    field: str
    op: str
    slot_name: str
    slot_value: Optional[Any] = None


class SemanticPattern(BaseModel):
    """
    Modelo de um Padrão Semântico de Consulta.
    Armazena a estrutura de intenção para reaproveitamento posterior.
    """
    id: str
    agent_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used_at: datetime = Field(default_factory=datetime.now)
    usage_count: int = 1
    success_count: int = 1
    failure_count: int = 0
    
    intent_family: str  # e.g., "SELECT", "COUNT", "SELECT_JOIN", "COUNT_JOIN"
    mode: str           # e.g., "list", "count"
    tables: list[str]
    join_path: Optional[dict] = None
    
    filters: list[PatternFilter] = Field(default_factory=list)
    order_by: list[dict] = Field(default_factory=list)
    limit: Optional[int] = None
    
    sql_template: str
    examples: list[dict] = Field(default_factory=list)
