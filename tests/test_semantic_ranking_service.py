import pytest
from datetime import datetime, timedelta
from app.schemas.semantic import SemanticPattern, PatternFilter
from app.services.semantic.semantic_ranking_service import (
    calculate_pattern_score, rank_candidates, should_auto_select
)

def create_mock_pattern(id: str, success: int, usage: int, failure: int, days_old: int) -> SemanticPattern:
    return SemanticPattern(
        id=id,
        agent_id="agent_1",
        intent_family="SELECT",
        mode="list",
        tables=["Projeto"],
        filters=[PatternFilter(field="A", op="=", slot_name="p0", slot_value="1")],
        sql_template="SELECT *",
        examples=[],
        usage_count=usage,
        success_count=success,
        failure_count=failure,
        last_used_at=datetime.now() - timedelta(days=days_old)
    )

def test_score_calculation():
    """Testa o cálculo composto do score."""
    p1 = create_mock_pattern("p1", success=10, usage=10, failure=0, days_old=0)
    cand1 = calculate_pattern_score(p1, is_transformed=False, full_filter_match=True)
    
    assert cand1.breakdown.structural_match_score == 1.0 # 0.40
    assert cand1.breakdown.slot_match_score == 1.0 # 0.15
    assert cand1.breakdown.mode_match_score == 1.0 # 0.10
    assert cand1.breakdown.usage_score == 0.5 # 10 / 20 * 0.15 = 0.075
    assert cand1.breakdown.success_score == 1.0 # 10 / 10 * 0.10 = 0.10
    assert cand1.breakdown.recency_score == 1.0 # 0 days * 0.10 = 0.10
    # Expected: 0.40+0.15+0.10+0.075+0.10+0.10 = 0.925 => ~0.925
    assert cand1.final_score > 0.9

def test_score_penalties():
    """Testa queda de score para targets transformados, velhos e de baixa taxa de sucesso."""
    p2 = create_mock_pattern("p2", success=1, usage=5, failure=4, days_old=15)
    cand2 = calculate_pattern_score(p2, is_transformed=True, full_filter_match=True)
    
    assert cand2.breakdown.mode_match_score == 0.8
    assert cand2.breakdown.recency_score == 0.5 # 15 days = 1.0 - 0.5 = 0.5
    assert cand2.breakdown.success_score < 0.3 # 1 acerto, 4 falhas (20%) * penalty = < 0.2
    assert cand2.final_score < 0.80

def test_rank_candidates():
    """Ordenação e margem matemática aplicadas corretamente."""
    p_best = create_mock_pattern("best", success=20, usage=20, failure=0, days_old=0)
    p_good = create_mock_pattern("good", success=10, usage=10, failure=0, days_old=5)
    p_bad = create_mock_pattern("bad", success=1, usage=1, failure=10, days_old=30)
    
    c1 = calculate_pattern_score(p_best, False)
    c2 = calculate_pattern_score(p_good, False)
    c3 = calculate_pattern_score(p_bad, False)
    
    ranked = rank_candidates([c2, c1, c3])
    
    assert ranked[0].pattern.id == "best"
    assert ranked[1].pattern.id == "good"
    assert ranked[2].pattern.id == "bad"
    assert ranked[0].final_score > ranked[1].final_score
    assert ranked[0].margin == round(ranked[0].final_score - ranked[1].final_score, 3)

def test_auto_select_dominant():
    """Deve auto-selecionar o canditato dominante se a margem for gorda e threshold mínimo superado."""
    p_best = create_mock_pattern("dominant", success=20, usage=20, failure=0, days_old=0)
    p_weak = create_mock_pattern("weak", success=1, usage=1, failure=5, days_old=29)
    
    c1 = calculate_pattern_score(p_best, False)
    c2 = calculate_pattern_score(p_weak, False)
    
    ranked = rank_candidates([c1, c2])
    
    selected = should_auto_select(ranked)
    assert selected is not None
    assert selected.pattern.id == "dominant"

def test_rejection_low_threshold():
    """8. Rejeição com safety cut (Scores muito ruins não devem ser selecionados)."""
    p_bad = create_mock_pattern("bad", success=0, usage=0, failure=5, days_old=60) # Decai muito
    
    # Criaremos fake candidato forçando final score
    c1 = calculate_pattern_score(p_bad, True)
    c1.final_score = 0.65 # Abaixo de 0.70
    
    ranked = rank_candidates([c1])
    selected = should_auto_select(ranked)
    assert selected is None

def test_rejection_ambiguity():
    """4. Rejeição quando scores estão muito próximos para garantir fallback invés de risco."""
    # Dois excelentes colidindo
    p1 = create_mock_pattern("A", success=20, usage=20, failure=0, days_old=0)
    p2 = create_mock_pattern("B", success=19, usage=19, failure=0, days_old=1)
    
    c1 = calculate_pattern_score(p1, False)
    c2 = calculate_pattern_score(p2, False)
    
    ranked = rank_candidates([c1, c2])
    assert ranked[0].margin < 0.10 # Ambiguidade clássica
    
    selected = should_auto_select(ranked)
    assert selected is None
