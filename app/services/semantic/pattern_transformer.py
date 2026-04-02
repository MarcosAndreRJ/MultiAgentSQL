from typing import Optional, Any
from app.core.logger import get_logger
from app.schemas.semantic import SemanticPattern
from app.services.query_builder import build_sql, V2Plan, BuildResult
from app.services.join_resolver import JoinPath
from app.schemas.digest import DBDigest

logger = get_logger("semantic_pattern_transformer")

def can_transform(pattern: SemanticPattern, target_intent: str) -> bool:
    """
    Verifica se a mudança de intenção (ex: SELECT -> COUNT) é suportada 
    e estruturalmente segura para este pattern.
    """
    p_intent = pattern.intent_family.upper()
    t_intent = target_intent.upper()
    
    # Se já é a mesma intenção, não precisamos "transformar" para adaptar o modo
    if p_intent == t_intent:
        return True

    # Comutações puras conhecidas:
    valid_transformations = [
        ("SELECT", "COUNT"),
        ("COUNT", "SELECT"),
        ("SELECT_JOIN", "COUNT_JOIN"),
        ("COUNT_JOIN", "SELECT_JOIN")
    ]
    
    if (p_intent, t_intent) in valid_transformations:
        return True
        
    return False

def transform_pattern(
    pattern: SemanticPattern, 
    target_intent: str, 
    request_slots: Any, 
    digest: DBDigest
) -> Optional[BuildResult]:
    """
    Reconstrói a query de forma limpa convertendo o modo de operação (list <-> count).
    Em vez de regex frágil na string SQL, reaproveitamos a fundação segura do query_builder
    injetando os slots e a nova intenção sobre o esqueleto do pattern.
    """
    if not can_transform(pattern, target_intent):
        logger.debug(f"[SEMANTIC_PATTERN_TRANSFORM_MISS] Não é possível transformar {pattern.intent_family} em {target_intent}")
        return None
        
    logger.info(f"[SEMANTIC_PATTERN_TRANSFORM_ATTEMPT] Tentando transformar {pattern.intent_family} -> {target_intent}")

    # Recupera estrutura de join se existir
    jp = None
    if pattern.join_path:
        jp = JoinPath(
            left_table=pattern.join_path["left_table"],
            right_table=pattern.join_path["right_table"],
            left_col=pattern.join_path["left_col"],
            right_col=pattern.join_path["right_col"]
        )

    # Adaptação contextual do modo
    order_by = request_slots.order_by
    limit = request_slots.limit
    
    if "COUNT" in target_intent:
        order_by = [] # Inútil em count
        limit = None  # Inútil em count

    # Construímos o plano híbrido: Intenção alvo + Estrutura do Pattern + Valores do Usuário
    plan = V2Plan(
        intent=target_intent,
        tables=pattern.tables,
        filters=request_slots.filters,
        order_by=order_by,
        limit=limit,
        join_path=jp,
        confidence=1.0 # Forçado, pois a origem é o Matcher Validado
    )
    
    build_result = build_sql(plan, digest)
    
    if build_result:
        logger.info(f"[SEMANTIC_PATTERN_TRANSFORM_SUCCESS] Transformação concluída. SQL re-builded: {build_result.sql}")
    else:
        logger.warning("[SEMANTIC_PATTERN_TRANSFORM_MISS] query_builder recusou a transformação.")
        
    return build_result
