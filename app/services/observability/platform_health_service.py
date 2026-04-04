import time
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.db import models as db_models
from app.schemas.health import HealthStatus, HealthDomain, PlatformHealthRead
from app.core.logger import get_logger
from app.core.settings import settings
from app.services.observability.execution_observability_service import generate_execution_id

logger = get_logger("observability.platform")

def check_platform_db_health(db: Session) -> PlatformHealthRead:
    """Verifica e reporta se o MySQL central está operacional."""
    start_time = time.time()
    status = HealthStatus.HEALTHY
    message = "Platform DB OK"
    latency = 0.0
    execution_id = generate_execution_id()

    try:
        # Executa query rápida de 'keep-alive'
        db.execute(text("SELECT 1"))
        latency = (time.time() - start_time) * 1000
    except Exception as e:
        status = HealthStatus.OFFLINE
        message = f"Falha crítica no platform_db: {str(e)}"
        logger.error(
            "OBSERVABILITY | execution_id=%s | DOMAIN=%s | STATUS=%s | MSG=%s",
            execution_id,
            HealthDomain.PLATFORM,
            status,
            message,
        )

    # Persiste log se possível
    _log_health(db, HealthDomain.PLATFORM, status, latency, message, execution_id=execution_id)

    # Mask base_url/host
    safe_url = settings.MYSQL_HOST if settings.MYSQL_HOST else "unknown"

    return PlatformHealthRead(
        status=status,
        latency_ms=round(latency, 2),
        message=message,
        domain=HealthDomain.PLATFORM,
        entity_name="Central MySQL (Platform)",
        database_url=safe_url
    )

def _log_health(db: Session, domain: HealthDomain, status: HealthStatus, latency: float, message: str, execution_id: str | None = None):
    """Persiste o resultado do check na tabela histórica."""
    try:
        log = db_models.HealthCheckLog(
            domain=domain,
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
        logger.warning(f"Não foi possível persistir health log: {e}")
