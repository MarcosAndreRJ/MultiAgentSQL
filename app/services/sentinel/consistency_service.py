"""
Service para Cálculo de Score de Consistência (Sentinel).
Mede estabilidade de latência e taxa de sucesso histórica.
"""
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import models as db_models
from app.core.logger import get_logger

logger = get_logger("sentinel.consistency")

def calculate_consistency_score(
    db: Session, 
    provider_id: int, 
    model_id: Optional[int] = None,
    lookback_hours: int = 24
) -> Dict[str, Any]:
    """
    Calcula score de 0 a 100 baseado em:
    - Taxa de Sucesso (60%)
    - Estabilidade de Latência (40%) - Medida via Coeficiente de Variação (CV)
    """
    since = datetime.utcnow() - timedelta(hours=lookback_hours)
    
    query = db.query(db_models.ProviderExecutionLog).filter(
        db_models.ProviderExecutionLog.provider_id == provider_id,
        db_models.ProviderExecutionLog.created_at >= since
    )
    
    if model_id:
        query = query.filter(db_models.ProviderExecutionLog.model_id == model_id)
    
    logs = query.all()
    
    if not logs:
        return {
            "score": 100, 
            "status": "stable", 
            "reason": "Sem execuções recentes para análise.",
            "sample_size": 0
        }

    total = len(logs)
    successes = len([l for l in logs if l.status == "success"])
    success_rate = (successes / total) * 100
    
    # Cálculo de Estabilidade de Latência (CV = std_dev / mean)
    latencies = [l.latency_ms for l in logs if l.status == "success" and l.latency_ms is not None]
    
    stability_factor = 100.0
    if len(latencies) > 1:
        mean_latency = statistics.mean(latencies)
        if mean_latency > 0:
            std_dev = statistics.stdev(latencies)
            cv = std_dev / mean_latency
            # Estabilidade: 100 - (CV * 100). Se CV for 0.2 (20% variação), estabilidade é 80.
            stability_factor = max(0, 100 - (cv * 100))
    elif len(latencies) == 1:
        stability_factor = 100.0
    else:
        stability_factor = 0.0 # Se tudo falhou, estabilidade é zero

    # Weighted Score
    final_score = int((success_rate * 0.6) + (stability_factor * 0.4))
    
    status = "stable"
    if final_score < 70:
        status = "critical"
    elif final_score < 90:
        status = "warning"
        
    reason = f"Baseado em {total} chamadas (Sucesso: {int(success_rate)}%, Estabilidade: {int(stability_factor)}%)."
    
    return {
        "score": final_score,
        "status": status,
        "reason": reason,
        "sample_size": total
    }

def update_consistency_scores(db: Session):
    """
    Atualiza a tabela de scores de consistência para todos os providers ativos.
    """
    providers = db.query(db_models.LLMProvider).filter(db_models.LLMProvider.is_active == True).all()
    
    for p in providers:
        # Score Global do Provider
        result = calculate_consistency_score(db, p.id)
        
        score_row = db_models.SentinelConsistencyScore(
            provider_id=p.id,
            model_id=None,
            score=result["score"],
            status=result["status"],
            reason=result["reason"]
        )
        db.add(score_row)
        
    db.commit()
    logger.info(f"Sentinel: Scores de consistência atualizados para {len(providers)} providers.")
