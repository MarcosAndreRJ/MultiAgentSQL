"""
Pydantic schemas para Providers (contratos API / DTOs).
Alinhado com a Etapa 4.2 operacional.

Observacoes de seguranca: ProviderRead NUNCA expõe a api_key real.
Usa-se o campo has_api_key para indicar se existe chave.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    CUSTOM = "custom"
    OTHER = "other"


class ProviderBase(BaseModel):
    name: str = Field(..., min_length=1)
    type: ProviderType = Field(..., description="Tipo do provider (openai, custom, etc)")
    base_url: Optional[str] = None
    is_active: bool = True
    config_json: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

    @field_validator("base_url")
    @classmethod
    def validate_custom_url(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("type") == ProviderType.CUSTOM and not v:
            raise ValueError("base_url is required for custom provider type")
        return v


class ProviderCreate(ProviderBase):
    api_key: Optional[str] = None  # aceita api_key em entrada (NUNCA será exposta)


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ProviderType] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

    @field_validator("base_url")
    @classmethod
    def validate_custom_url(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("type") == ProviderType.CUSTOM and not v:
            raise ValueError("base_url is required for custom provider type")
        return v


class ProviderRead(ProviderBase):
    id: int
    has_api_key: bool = False
    api_key: Optional[str] = None  # Incluído somente em detalhamento (GET /{id})
    
    last_status: Optional[str] = None
    last_test_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProviderList(BaseModel):
    providers: List[ProviderRead]

    model_config = {"from_attributes": True}
