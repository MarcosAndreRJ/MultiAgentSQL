import os
import time
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.health import HealthStatus, SystemHealthSummaryRead
from app.services.observability.platform_health_service import check_platform_db_health
from app.services.observability.provider_health_service import get_all_providers_health
from app.services.observability.target_db_health_service import get_all_target_dbs_health
from app.core.logger import get_logger

logger = get_logger("observability.system")

async def get_system_health_summary(db: Session) -> SystemHealthSummaryRead:
    """Consolida a visão geral de saúde da plataforma (Assíncrono)."""
    
    # 1. Platform DB Health
    platform_health = check_platform_db_health(db)
    
    # 2. Providers Health (Chamada agora assíncrona)
    providers_health = await get_all_providers_health(db)
    
    # 3. Target DBs Health
    target_dbs_health = get_all_target_dbs_health(db)
    
    # 4. Runtime Info
    import time
    from datetime import datetime
    
    runtime = {
        "os": os.name,
        "pid": os.getpid(),
        "uptime_seconds": 0, # Placeholder
        "memory_usage_mb": 0.0,
        "cpu_usage_percent": 0.0,
        "checked_at": datetime.utcnow().isoformat()
    }
    
    # 5. Determine Overall Status
    overall_status = HealthStatus.HEALTHY
    
    if platform_health.status != HealthStatus.HEALTHY:
        overall_status = HealthStatus.OFFLINE
    elif any(p.status != HealthStatus.HEALTHY for p in providers_health) or \
         any(t.status != HealthStatus.HEALTHY for t in target_dbs_health):
        overall_status = HealthStatus.DEGRADED

    return SystemHealthSummaryRead(
        overall_status=overall_status,
        platform=platform_health,
        providers=providers_health,
        target_dbs=target_dbs_health,
        runtime=runtime
    )

