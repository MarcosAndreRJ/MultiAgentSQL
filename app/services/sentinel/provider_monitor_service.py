"""
Service Orquestrador de Monitoramento (Sentinel).
Executa o ciclo completo para um provider específico.
"""
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db import models as db_models
from app.services.platform import provider_service
from app.services.sentinel import credits_service
from app.core.logger import get_logger

logger = get_logger("sentinel.monitor")


async def monitor_provider(db: Session, provider_id: int) -> Dict[str, Any]:
    """
    Executa o ciclo Sentinel para um único provider (assíncrono):
    1. Sincroniza modelos
    2. Coleta créditos
    3. Registra snapshot
    """
    provider = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.id == provider_id).first()
    if not provider or not provider.is_active:
        return {"id": provider_id, "status": "skipped", "reason": "not_found_or_inactive"}

    try:
        sync_result = await provider_service.sync_provider_models(db, provider_id)
        credits = await credits_service.fetch_provider_credits(provider)

        models_synced = int(sync_result.get("models_synced", 0) or 0)
        credits_status = credits.get("status")

        if models_synced == 0:
            snapshot_status = "critical"
            message = "Nenhum modelo sincronizado no ciclo."
        elif credits_status == "error":
            snapshot_status = "degraded"
            message = credits.get("details") or "Erro na coleta de créditos."
        else:
            snapshot_status = "healthy"
            message = credits.get("details") or f"Synced {models_synced} models."

        snapshot = db_models.SentinelSnapshot(
            provider_id=provider_id,
            checked_at=datetime.utcnow(),
            models_total=models_synced,
            models_new=int(sync_result.get("new", 0) or 0),
            models_updated=int(sync_result.get("updated", 0) or 0),
            models_unavailable=int(sync_result.get("marked_unavailable", 0) or 0),
            credits_available=credits.get("amount"),
            credits_currency=credits.get("currency"),
            status=snapshot_status,
            message=message,
        )
        db.add(snapshot)
        db.commit()

        return {
            "id": provider_id,
            "name": provider.name,
            "models_synced": models_synced,
            "credits_status": credits_status,
            "status": snapshot_status,
            "message": message,
        }
    except Exception as e:
        logger.error("Erro no monitoramento do provider %s: %s", provider_id, str(e))
        snapshot = db_models.SentinelSnapshot(
            provider_id=provider_id,
            checked_at=datetime.utcnow(),
            status="critical",
            message=str(e),
        )
        db.add(snapshot)
        db.commit()
        return {"id": provider_id, "status": "error", "reason": str(e)}


async def run_sentinel_cycle(db: Session):
    """Executa o ciclo completo para todos os providers ativos."""
    providers = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.is_active == True).all()
    results = []

    for provider in providers:
        results.append(await monitor_provider(db, provider.id))

    return results
