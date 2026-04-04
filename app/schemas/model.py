"""Pydantic schemas para Models (contratos de API)."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


from app.schemas.provider import ProviderRead

class ModelRead(BaseModel):
    """Schema de leitura para Modelos (JSON puro, sem HTML)."""
    id: int
    model_id: str = Field(..., description="Identificador técnico do modelo")
    display_name: str = Field(..., description="Nome de exibição")
    provider_id: int
    provider_name: Optional[str] = Field(None, description="Nome do provider")
    context_window: Optional[int] = Field(default=None, description="Janela de contexto (tokens)")
    supports_tools: bool = Field(default=False, description="Suporta tool calling")
    supports_json: bool = Field(default=False, description="Suporta modo JSON")
    supports_streaming: bool = Field(default=True, description="Suporta streaming")
    is_available: bool = Field(default=True, description="Disponibilidade técnica")
    is_active: bool = Field(default=True, description="Ativo para uso (governança)")
    status: str = Field(default="active", description="Status compatível (active/inactive)")
    source: str = Field(default="sync", description="Origem: sync, manual, bootstrap")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProviderCatalogRead(BaseModel):
    """Agrupamento de modelos por provedor."""
    provider: ProviderRead
    models: List[ModelRead]


class ModelList(BaseModel):
    models: List[ModelRead]
