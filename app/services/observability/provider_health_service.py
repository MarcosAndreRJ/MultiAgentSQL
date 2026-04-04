from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db import models as db_models
from app.schemas.health import HealthStatus, HealthDomain, ProviderHealthRead
from app.services.platform.provider_service import test_provider_connection
from app.core.logger import get_logger
from app.services.observability.execution_observability_service import generate_execution_id

logger = get_logger("observability.providers")

async def get_all_providers_health(db: Session) -> List[ProviderHealthRead]:
    """Itera sobre providers ativos e retorna o estado de saúde de cada um (Assíncrono)."""
    providers = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.is_active == True).all()
    results = []

    for p in providers:
        execution_id = generate_execution_id()
        # Chamada assíncrona
        test_result = await test_provider_connection(db, p.id)
        
        status = HealthStatus.HEALTHY if test_result["status"] == "ok" else HealthStatus.OFFLINE
        latency = float(test_result.get("latency_ms", 0.0))
        message = test_result.get("details") or test_result.get("error") or "Provider Online"


        # Logs estruturados
        logger.info(
            "OBSERVABILITY | execution_id=%s | DOMAIN=%s | ENTITY=%s/%s | STATUS=%s | LATENCY=%sms",
            execution_id,
            HealthDomain.PROVIDER,
            p.id,
            p.name,
            status,
            latency,
        )

        # Persiste no histórico
        _log_health(db, p, status, latency, message, execution_id=execution_id)

        results.append(ProviderHealthRead(
            status=status,
            latency_ms=round(latency, 2),
            message=message,
            domain=HealthDomain.PROVIDER,
            entity_id=str(p.id),
            entity_name=p.name,
            provider_type=p.provider_type
        ))

    return results

def _log_health(db: Session, provider: db_models.LLMProvider, status: HealthStatus, latency: float, message: str, execution_id: str | None = None):
    """Persiste o resultado do check na tabela histórica."""
    try:
        log = db_models.HealthCheckLog(
            domain=HealthDomain.PROVIDER,
            entity_id=str(provider.id),
            entity_name=provider.name,
            status=status,
            latency_ms=int(latency),
            message=message[:255] if message else None,
            execution_id=execution_id,
            checked_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Não foi possível persistir health log para provider {provider.id}: {e}")
