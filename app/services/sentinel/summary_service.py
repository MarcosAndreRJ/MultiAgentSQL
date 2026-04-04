"""
Service Aggregator para a Tela Sentinel (UI Dashboard).
Consolida métricas de snapshots e scores históricos.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import models as db_models
from app.core.logger import get_logger

logger = get_logger("sentinel.summary")


def _latest_snapshot_subquery(db: Session):
    return db.query(
        db_models.SentinelSnapshot.provider_id,
        func.max(db_models.SentinelSnapshot.checked_at).label("max_date")
    ).group_by(db_models.SentinelSnapshot.provider_id).subquery()


def get_sentinel_summary_data(db: Session) -> Dict[str, Any]:
    """Retorna o payload para os cards de resumo do Sentinel."""
    since = datetime.utcnow() - timedelta(hours=24)

    anomalies_count = db.query(db_models.SentinelSnapshot).filter(
        db_models.SentinelSnapshot.status == "critical",
        db_models.SentinelSnapshot.checked_at >= since
    ).count()

    providers = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.is_active == True).all()

    latest_scores = []
    for provider in providers:
        # Só incluímos no resumo global o score se o provider estiver saudável no último snapshot
        last_snap = db.query(db_models.SentinelSnapshot).filter(
            db_models.SentinelSnapshot.provider_id == provider.id
        ).order_by(db_models.SentinelSnapshot.checked_at.desc()).first()
        
        if last_snap and last_snap.status != "critical":
            score_row = db.query(db_models.SentinelConsistencyScore).filter(
                db_models.SentinelConsistencyScore.provider_id == provider.id
            ).order_by(db_models.SentinelConsistencyScore.calculated_at.desc()).first()
            if score_row:
                latest_scores.append(score_row.score)

    avg_score = (sum(latest_scores) / len(latest_scores)) if latest_scores else 0

    snapshot_subquery = _latest_snapshot_subquery(db)
    latest_snapshots = db.query(db_models.SentinelSnapshot).join(
        snapshot_subquery,
        (db_models.SentinelSnapshot.provider_id == snapshot_subquery.c.provider_id) &
        (db_models.SentinelSnapshot.checked_at == snapshot_subquery.c.max_date)
    ).all()

    critical_providers = [s for s in latest_snapshots if s.status == "critical"]
    degraded_providers = [s for s in latest_snapshots if s.status == "degraded"]
    healthy_providers = [s for s in latest_snapshots if s.status == "healthy"]

    last_run = db.query(func.max(db_models.SentinelSnapshot.checked_at)).scalar()

    from app.core.settings import settings
    interval = settings.SENTINEL_INTERVAL_MINUTES

    next_run_at = None
    if last_run:
        next_run_at = (last_run + timedelta(minutes=interval)).isoformat()

    return {
        "anomalies_detected": anomalies_count,
        "average_quality_score": round(avg_score, 1),
        "active_alerts": len(critical_providers),
        "providers_total": len(providers),
        "providers_healthy": len(healthy_providers),
        "providers_degraded": len(degraded_providers),
        "providers_critical": len(critical_providers),
        "last_run_at": last_run.isoformat() if last_run else None,
        "next_run_at": next_run_at,
        "critical_provider_names": [p.provider.name for p in critical_providers if p.provider],
        "sentinel_interval_minutes": interval
    }


def get_sentinel_providers_overview(db: Session) -> List[Dict[str, Any]]:
    """Retorna a lista de providers com seus últimos dados Sentinel enriquecidos."""
    providers = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.is_active == True).all()
    results = []

    for provider in providers:
        # Último snapshot (qualquer status)
        snapshot = db.query(db_models.SentinelSnapshot).filter(
            db_models.SentinelSnapshot.provider_id == provider.id
        ).order_by(db_models.SentinelSnapshot.checked_at.desc()).first()

        # Último snapshot bem-sucedido (para histórico)
        last_success = db.query(db_models.SentinelSnapshot).filter(
            db_models.SentinelSnapshot.provider_id == provider.id,
            db_models.SentinelSnapshot.status != "critical"
        ).order_by(db_models.SentinelSnapshot.checked_at.desc()).first()

        # Score de consistência
        score_record = db.query(db_models.SentinelConsistencyScore).filter(
            db_models.SentinelConsistencyScore.provider_id == provider.id
        ).order_by(db_models.SentinelConsistencyScore.calculated_at.desc()).first()

        # Tendência (ultimos 10)
        recent_snapshots = db.query(db_models.SentinelSnapshot).filter(
            db_models.SentinelSnapshot.provider_id == provider.id
        ).order_by(db_models.SentinelSnapshot.checked_at.desc()).limit(10).all()
        trend = [s.status for s in reversed(recent_snapshots)]

        # Contagem real de modelos no catálogo
        total_models_registered = db.query(db_models.LLMModel).filter(
            db_models.LLMModel.provider_id == provider.id
        ).count()

        is_reachable = snapshot.status != "critical" if snapshot else False
        
        # Só expõe o score se o provider estiver alcançável no ciclo atual
        current_score = score_record.score if (score_record and is_reachable) else None

        results.append({
            "provider_id": provider.id,
            "provider_name": provider.name,
            "is_reachable": is_reachable,
            "last_checked_at": snapshot.checked_at.isoformat() if snapshot else None,
            "last_successful_check_at": last_success.checked_at.isoformat() if last_success else None,
            "models_checked": snapshot.models_total if snapshot else 0,
            "models_registered": total_models_registered,
            "models_unavailable": snapshot.models_unavailable if snapshot else 0,
            "credits_available": snapshot.credits_available if snapshot else None,
            "credits_currency": snapshot.credits_currency if snapshot else None,
            "consistency_score": current_score,
            "last_valid_consistency_score": score_record.score if score_record else None,
            "status": snapshot.status if snapshot else "unknown",
            "message": snapshot.message if snapshot else None,
            "trend": trend,
        })

    return results


def get_provider_history(db: Session, provider_id: int, hours: int = 24, limit: int = 100) -> Dict[str, Any]:
    """Retorna histórico de snapshots de um provider para drilldown no dashboard."""
    since = datetime.utcnow() - timedelta(hours=max(hours, 1))
    rows = db.query(db_models.SentinelSnapshot).filter(
        db_models.SentinelSnapshot.provider_id == provider_id,
        db_models.SentinelSnapshot.checked_at >= since
    ).order_by(db_models.SentinelSnapshot.checked_at.desc()).limit(min(max(limit, 1), 500)).all()

    return {
        "provider_id": provider_id,
        "hours": hours,
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
                "status": r.status,
                "models_total": r.models_total,
                "models_new": r.models_new,
                "models_updated": r.models_updated,
                "models_unavailable": r.models_unavailable,
                "credits_available": r.credits_available,
                "credits_currency": r.credits_currency,
                "message": r.message,
            }
            for r in rows
        ]
    }
