"""
Schemas para comunicação de chat (mensagens e sessões).
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ChatMessage(BaseModel):
    """Mensagem de entrada do usuário."""
    agent_id: str
    session_id: str
    message: str
    attached_files: list[str] = Field(default_factory=list)


class MessageRole(str):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class HistoryMessage(BaseModel):
    """Mensagem no histórico da sessão."""
    id: Optional[str] = Field(default=None, description="UUID único para a mensagem/evento")
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    type: str = "message"  # "message" | "event"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict) # run_id, step, status, etc.


class LLMPlan(BaseModel):
    """Plano estruturado gerado pelo LLM."""
    intent: str  # "query" | "write" | "ddl" | "explain" | "mockdata" | "unknown"
    needs_tools: bool
    tools: list[dict] = Field(default_factory=list)
    sql: Optional[str] = None
    explanation: str = ""
    risk_hint: str = "low"  # "low" | "medium" | "high"

    model_config = ConfigDict(extra="allow")


class ChatResponse(BaseModel):
    """Resposta da API de chat."""
    session_id: str
    agent_id: str
    response: str
    sql_generated: Optional[str] = None
    sql_executed: Optional[str] = None
    pending_action_id: Optional[str] = None
    execution_result: Optional[dict] = None
    risk_level: Optional[str] = None
    model: Optional[str] = None
    execution_source: Optional[str] = None
    used_llm: bool = False
    latency_ms: Optional[float] = None
    status: str = "completed"  # "completed" | "pending_confirmation" | "error"
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Session(BaseModel):
    """Estado da sessão de um agente."""
    session_id: str
    agent_id: str
    channel: str = "web"
    current_goal: Optional[str] = None
    active_skills: list[str] = Field(default_factory=list)
    recent_objects: dict = Field(default_factory=lambda: {"tables": [], "views": [], "triggers": []})
    last_sql_generated: Optional[str] = None
    last_sql_executed: Optional[str] = None
    pending_actions: list[dict] = Field(default_factory=list)
    last_changes: list[dict] = Field(default_factory=list)
    user_preferences: dict = Field(default_factory=dict)
    history: list[HistoryMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
