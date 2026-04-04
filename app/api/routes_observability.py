from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.observability.execution_observability_service import (
    list_agent_observability_metrics,
    list_agent_execution_logs,
)

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/agents")
async def get_agents_observability(db: Session = Depends(get_db)):
    """Métricas básicas por agente: volume, taxa de sucesso, latência média e última execução."""
    items = list_agent_observability_metrics(db)
    return {"items": items, "total": len(items)}


@router.get("/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    """Lista detalhada dos logs de execução de um agente com paginação."""
    return list_agent_execution_logs(db, agent_id=agent_id, page=page, page_size=page_size)
