from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db import models as db_models
from app.schemas.health import (
    PlatformHealthRead, 
    ProviderHealthRead, 
    TargetDbHealthRead, 
    SystemHealthSummaryRead
)
from app.services.observability import (
    platform_health_service,
    provider_health_service,
    target_db_health_service,
    system_health_service
)

router = APIRouter(prefix="/api/health", tags=["observability", "health"])

@router.get("/database", response_model=PlatformHealthRead)
async def get_database_health(db: Session = Depends(get_db)):
    """Verifica saúde do banco da plataforma (MySQL Central)."""
    # Serviço síncrono, mas roteador é async
    return platform_health_service.check_platform_db_health(db)

@router.get("/runtime")
async def get_runtime_health():
    """Verifica saúde do runtime Python/FastAPI."""
    # Retorna status básico de runtime
    return {
        "status": "healthy",
        "uptime_seconds": 0, # Placeholder
        "version": "1.0.0",
        "domain": "runtime"
    }

@router.get("/providers", response_model=List[ProviderHealthRead])
async def get_providers_health(db: Session = Depends(get_db)):
    """Verifica conectividade com todos os providers LLM ativos (Async)."""
    return await provider_health_service.get_all_providers_health(db)

@router.get("/target-dbs", response_model=List[TargetDbHealthRead])
async def get_target_dbs_health(db: Session = Depends(get_db)):
    """Verifica conectividade com bancos operacionais (target databases)."""
    return target_db_health_service.get_all_target_dbs_health(db)

@router.get("/summary", response_model=SystemHealthSummaryRead)
async def get_health_summary(db: Session = Depends(get_db)):
    """Visão consolidada do estado operacional do sistema (Async)."""
    return await system_health_service.get_system_health_summary(db)



@router.get("/logs", response_model=List[dict])
async def get_health_logs(db: Session = Depends(get_db), limit: int = 50):
    """Retorna os últimos logs históricos de integridade do sistema."""
    logs = db.query(db_models.HealthCheckLog).order_by(db_models.HealthCheckLog.checked_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "domain": l.domain,
            "entity_id": l.entity_id,
            "entity_name": l.entity_name,
            "status": l.status,
            "latency_ms": l.latency_ms,
            "message": l.message,
            "execution_id": l.execution_id,
            "checked_at": l.checked_at
        } for l in logs
    ]
