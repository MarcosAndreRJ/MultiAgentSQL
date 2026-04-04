"""
Router da API para Observabilidade Sentinel.
Alimenta o dashboard com métricas reais de saúde e consistência.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.session import get_db, SessionLocal
from app.services.sentinel import summary_service, provider_monitor_service, consistency_service
from app.core.logger import get_logger

logger = get_logger("api.sentinel")

router = APIRouter(prefix="/api/sentinel", tags=["Observabilidade - Sentinel"])


@router.get("/summary", response_model=Dict[str, Any])
def get_summary(db: Session = Depends(get_db)):
    """Retorna resumo consolidado para os cards do dashboard Sentinel."""
    try:
        return summary_service.get_sentinel_summary_data(db)
    except Exception as e:
        logger.error("Erro no summary sentinel: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=List[Dict[str, Any]])
def list_sentinel_providers(db: Session = Depends(get_db)):
    """Retorna visão geral de todos os providers com dados Sentinel."""
    try:
        return summary_service.get_sentinel_providers_overview(db)
    except Exception as e:
        logger.error("Erro no providers sentinel: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}/history", response_model=Dict[str, Any])
def get_provider_history(provider_id: int, hours: int = 24, limit: int = 100, db: Session = Depends(get_db)):
    """Histórico detalhado de snapshots por provider."""
    try:
        return summary_service.get_provider_history(db, provider_id, hours=hours, limit=limit)
    except Exception as e:
        logger.error("Erro no histórico sentinel provider=%s: %s", provider_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _run_manual_cycle_task(trigger_id: str):
    db = SessionLocal()
    try:
        results = await provider_monitor_service.run_sentinel_cycle(db)
        consistency_service.update_consistency_scores(db)
        logger.info("Sentinel manual cycle finalizado | trigger_id=%s | providers=%s", trigger_id, len(results))
    except Exception as e:
        logger.error("Erro no ciclo manual sentinel | trigger_id=%s | error=%s", trigger_id, str(e))
    finally:
        db.close()


@router.post("/run", response_model=Dict[str, Any])
async def trigger_manual_run(background_tasks: BackgroundTasks, async_mode: bool = True, db: Session = Depends(get_db)):
    """Dispara um ciclo manual do Sentinel (assíncrono por padrão)."""
    try:
        trigger_id = f"sentinel_{uuid.uuid4().hex[:10]}"

        if async_mode:
            background_tasks.add_task(_run_manual_cycle_task, trigger_id)
            return {
                "status": "accepted",
                "trigger_id": trigger_id,
                "message": "Ciclo Sentinel enfileirado em background."
            }

        results = await provider_monitor_service.run_sentinel_cycle(db)
        consistency_service.update_consistency_scores(db)
        return {
            "status": "success",
            "trigger_id": trigger_id,
            "message": "Ciclo Sentinel finalizado.",
            "results": results
        }
    except Exception as e:
        logger.error("Erro no manual switch sentinel: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consistency")
def get_consistency_history(db: Session = Depends(get_db)):
    """Retorna visão de consistência atual (compat)."""
    return {"message": "Use /api/sentinel/providers e /api/sentinel/providers/{id}/history para drilldown."}
