from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel
from app.schemas.semantic import SemanticPattern
from app.core.logger import get_logger

logger = get_logger("semantic_ranking_service")

class ScoreBreakdown(BaseModel):
    structural_match_score: float
    slot_match_score: float
    mode_match_score: float
    usage_score: float
    success_score: float
    recency_score: float

class RankedCandidate(BaseModel):
    pattern: SemanticPattern
    final_score: float
    margin: float = 0.0
    breakdown: ScoreBreakdown
    reasons: list[str]
    transformed_result: Optional[Any] = None

def calculate_pattern_score(
    pattern: SemanticPattern, 
    is_transformed: bool,
    full_filter_match: bool = True,
    enrichment_detected: bool = False
) -> RankedCandidate:
    
    reasons = []
    
    # 0. Bloqueio de Expansão de Projeção (Regra de Ouro)
    # Se o usuário pediu colunas extras/enriquecimento e o pattern é uma listagem simples,
    # devemos invalidar o match para forçar o fallback (LLM ou outro agente).
    projection_blocked = False
    if enrichment_detected and "SELECT" in pattern.intent_family:
        # Nota: Só bloqueamos se o pattern for SELECT (listagem) ou SELECT_JOIN
        # Se for um pattern que já era complexo, talvez ele cubra, mas na dúvida,
        # padrões de "SELECT *" salvos via V2/FastPath são simplistas.
        projection_blocked = True
        reasons.append("BLOQUEADO: Expansão de projeção detectada na mensagem (colunas extras pedidas)")

    # 1. Structural Match (1.0 se as tabelas e a estrutura batem)
    structural_match_score = 1.0 if not projection_blocked else 0.0
    if not projection_blocked:
        reasons.append("Tabela e assinaturas compatíveis")
    
    # 2. Slot Match
    slot_match_score = 1.0 if full_filter_match else 0.5
    if full_filter_match:
        reasons.append("Filtros perfeitamente compatíveis")
        
    # 3. Mode Match
    mode_match_score = 0.8 if is_transformed else 1.0
    if is_transformed:
        reasons.append("Modo adaptado com segurança (List <-> Count)")
    else:
        reasons.append("Modo de operação idêntico")
        
    # 4. Usage Score (Normalizado para no máx 20 usos)
    usage_score = min(1.0, pattern.usage_count / 20.0)
    if usage_score > 0.5:
        reasons.append(f"Alta frequência de uso ({pattern.usage_count} vezes)")
        
    # 5. Success Score (Taxa de sucesso)
    total_attempts = pattern.success_count + pattern.failure_count
    if total_attempts > 0:
        success_score = pattern.success_count / total_attempts
    else:
        success_score = 1.0 # Padrões novos começam otimistas
        
    if success_score > 0.8 and total_attempts > 1:
        reasons.append(f"Alto índice de acerto ({success_score * 100:.0f}%)")
    elif total_attempts > 2 and success_score < 0.5:
        reasons.append(f"Histórico recente de falhas detectado")
        success_score = success_score * 0.5 # Penaliza
        
    # 6. Recency Score (Decai progressivamente ao longo de 30 dias)
    # Proteção de conversão caso Pydantic não tenha hidratado
    last = pattern.last_used_at
    if not isinstance(last, datetime):
        last = datetime.fromisoformat(str(last))
        
    days_old = max(0, (datetime.now() - last).days)
    recency_score = max(0.1, 1.0 - (days_old / 30.0))
    if days_old < 3:
        reasons.append("Consultado recentemente (alta recência)")

    final_score = (
        structural_match_score * 0.40 +
        slot_match_score       * 0.15 +
        mode_match_score       * 0.10 +
        usage_score            * 0.15 +
        success_score          * 0.10 +
        recency_score          * 0.10
    )

    return RankedCandidate(
        pattern=pattern,
        final_score=round(final_score, 3),
        breakdown=ScoreBreakdown(
            structural_match_score=structural_match_score,
            slot_match_score=slot_match_score,
            mode_match_score=mode_match_score,
            usage_score=usage_score,
            success_score=success_score,
            recency_score=recency_score
        ),
        reasons=reasons
    )

def rank_candidates(candidates: list[RankedCandidate]) -> list[RankedCandidate]:
    """Ordena os candidatos do maior para o menor score, preenchendo as margens."""
    ranked = sorted(candidates, key=lambda c: c.final_score, reverse=True)
    
    for i in range(len(ranked)):
        if i < len(ranked) - 1:
            ranked[i].margin = round(ranked[i].final_score - ranked[i+1].final_score, 3)
        else:
            ranked[i].margin = round(ranked[i].final_score, 3) # O último compete com zero
            
    return ranked

def should_auto_select(ranked_candidates: list[RankedCandidate]) -> Optional[RankedCandidate]:
    """
    Toma a decisão analítica de escolha. Retorna None em cenário de ambiguidade que requeira Fallback.
    Thresholds rígidos para garantir integridade.
    """
    if not ranked_candidates:
        return None
        
    best = ranked_candidates[0]
    
    # 1. Deve superar a nota de corte mínima de segurança (ex: 0.70)
    if best.final_score < 0.70:
        logger.info(f"[SEMANTIC_PATTERN_SELECTION_REJECTED] Melhor pattern {best.pattern.id} falhou no Threshold: {best.final_score} < 0.70")
        return None
        
    # 2. Se houver mais de um candidato, a vitória deve ser indubitável (>10% de margem)
    if len(ranked_candidates) > 1 and best.margin < 0.10:
        second = ranked_candidates[1]
        logger.warning(
            f"[SEMANTIC_PATTERN_SELECTION_REJECTED] Ambiguidade: Pattern {best.pattern.id} (Score: {best.final_score}) "
            f"conflita com {second.pattern.id} (Score: {second.final_score}). Margem: {best.margin} < 0.10"
        )
        return None
        
    logger.info(
        f"[SEMANTIC_PATTERN_SELECTED] Escolhido: {best.pattern.id} com score={best.final_score} e margem={best.margin}"
    )
    
    # Log estruturado da explicabilidade para dashboards e observabilidade
    log_data = {
        "pattern_id": best.pattern.id,
        "final_score": best.final_score,
        "score_breakdown": best.breakdown.model_dump(),
        "reasons": best.reasons
    }
    logger.debug(f"[SEMANTIC_PATTERN_DECISION_EXPLAINER] {log_data}")
    
    return best
