from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class HealthDomain(str, Enum):
    PLATFORM = "platform"
    PROVIDER = "provider"
    TARGET_DB = "target_db"
    RUNTIME = "runtime"


class HealthCheckRead(BaseModel):
    """Base schema para resumo de saúde de uma entidade."""
    status: HealthStatus
    latency_ms: Optional[float] = None
    last_checked_at: datetime = Field(default_factory=datetime.utcnow)
    message: Optional[str] = None
    domain: HealthDomain
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class PlatformHealthRead(HealthCheckRead):
    """Saúde do MySQL da plataforma."""
    database_url: Optional[str] = None  # Masked version


class ProviderHealthRead(HealthCheckRead):
    """Saúde de um provider LLM."""
    provider_type: str


class TargetDbHealthRead(HealthCheckRead):
    """Saúde de um banco operacional (Target DB)."""
    db_type: str
    host: str


class SystemHealthSummaryRead(BaseModel):
    """Visão consolidada de toda a infraestrutura."""
    overall_status: HealthStatus
    platform: PlatformHealthRead
    providers: List[ProviderHealthRead]
    target_dbs: List[TargetDbHealthRead]
    runtime: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
