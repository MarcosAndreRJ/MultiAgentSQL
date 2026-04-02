"""
Schemas para pending actions (ações aguardando confirmação do usuário).
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class PendingAction(BaseModel):
    """Ação pendente aguardando confirmação."""
    id: str
    agent_id: str
    session_id: str
    conversation_id: Optional[str] = None
    database: Optional[str] = None
    sql: str
    action_type: str   # "DELETE" | "DROP" | "TRUNCATE" | etc.
    risk_level: str    # "high" | "medium"
    summary: str       # Descrição em linguagem natural
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    status: str = "pending"  # "pending" | "confirmed" | "cancelled" | "executed" | "expired"
    executed_at: Optional[datetime] = None
    execution_result: Optional[dict] = None


class PendingActionCreate(BaseModel):
    """Dados para criar uma nova pending action."""
    agent_id: str
    session_id: str
    database: Optional[str] = None
    sql: str
    action_type: str
    risk_level: str
    summary: str


class PendingActionConfirm(BaseModel):
    """Confirmação de uma pending action."""
    action_id: str
    agent_id: str
    session_id: str


class PendingActionCancel(BaseModel):
    """Cancelamento de uma pending action."""
    action_id: str
    agent_id: str
    session_id: str


class PendingActionList(BaseModel):
    """Lista de pending actions."""
    actions: list[PendingAction] = Field(default_factory=list)
    total: int = 0
