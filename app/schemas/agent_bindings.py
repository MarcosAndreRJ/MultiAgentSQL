"""
Pydantic schemas (DTOs) para Agent ⇄ Bindings (LLM e Target DB).

Esses schemas servem como contratos de API/serviço para leitura e
operações futuras. Saídas NUNCA expõem segredos (password).
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentLLMBindingBase(BaseModel):
    agent_id: str
    provider_id: int
    model_id: int
    is_default: bool = False
    fallback_order: int = 0
    supports_json_required: bool = False
    supports_tools_required: bool = False
    # New fields
    fallback_provider_id: Optional[int] = None
    fallback_model_id: Optional[int] = None
    require_streaming: bool = False
    min_context_window: Optional[int] = None
    is_active: bool = True


class AgentLLMBindingCreate(AgentLLMBindingBase):
    """Schema de entrada para criar um binding LLM (validação leve)."""


class AgentLLMBindingUpdate(BaseModel):
    provider_id: Optional[int]
    model_id: Optional[int]
    is_default: Optional[bool]
    fallback_order: Optional[int]
    supports_json_required: Optional[bool]
    supports_tools_required: Optional[bool]


class AgentLLMBindingRead(AgentLLMBindingBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    # Note: relationships are not expanded here to keep API minimal

    model_config = {"from_attributes": True}


class AgentDatabaseBindingBase(BaseModel):
    agent_id: str
    db_type: str = Field(default="mysql")
    host: str
    port: int = Field(default=3306)
    database_name: str
    schema_name: Optional[str] = None
    username: str
    connection_label: str = Field(default="default")
    is_active: bool = True
    is_default: bool = False
    read_only: bool = True


class AgentDatabaseBindingCreate(AgentDatabaseBindingBase):
    # senha só em entrada
    password: str


class AgentDatabaseBindingUpdate(BaseModel):
    host: Optional[str]
    port: Optional[int]
    database_name: Optional[str]
    schema_name: Optional[str]
    username: Optional[str]
    password: Optional[str]
    connection_label: Optional[str]
    is_active: Optional[bool]
    is_default: Optional[bool]
    read_only: Optional[bool]


class AgentDatabaseBindingRead(AgentDatabaseBindingBase):
    id: int
    # Nunca incluir password — apenas indicar se existe
    has_password: bool = False
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AgentRuntimeBindingSummary(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None
    llm_binding: Optional[AgentLLMBindingRead] = None
    target_db_binding: Optional[AgentDatabaseBindingRead] = None
    has_default_llm_binding: bool = False
    has_default_target_db_binding: bool = False
    status: str = "unknown"

    model_config = {"from_attributes": True}
