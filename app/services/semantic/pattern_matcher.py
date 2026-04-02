import re
from typing import Optional

from app.core.logger import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.chat import Session
from app.schemas.execution import DBExecuteRequest
from app.services import analytics_service
from app.services.alias_service import resolve_message_aliases
from app.services.digest_service import load_digest
from app.services.fastpath_service import FastPathResult
from app.services.fastpath_v2_service import _find_tables_in_message, _COUNT_KEYWORDS, _format_response
from app.services.filter_parser import parse_slots
from app.services.join_resolver import find_join_chain
from app.services.semantic.pattern_store import load_patterns, update_pattern_usage, SemanticPattern
from app.services.semantic.semantic_ranking_service import calculate_pattern_score, rank_candidates, should_auto_select
from app.tools import db_execute
from datetime import datetime

logger = get_logger("semantic_pattern_matcher")



async def match_and_execute(
    agent: AgentConfig,
    message: str,
    session: Session
) -> Optional[FastPathResult]:
    """
    Tenta encontrar um padrão semântico prévio que se encaixe na intenção atual.
    Se encontrar, substitui os slots variables e executa sem acionar LLM.
    """
    agent_id = agent.id
    patterns = load_patterns(agent_id)
    if not patterns:
        return None

    digest = load_digest(agent_id)
    if not digest:
        return None

    resolved_msg, alias_hits = resolve_message_aliases(agent_id, message)
    tables_found = _find_tables_in_message(resolved_msg, digest)

    if not tables_found:
        return None

    slots = parse_slots(resolved_msg)
    is_count_query = bool(_COUNT_KEYWORDS.search(resolved_msg))
    base_intent = "COUNT" if is_count_query else "SELECT"
    
    join_path = None
    if len(tables_found) == 2:
        chain = find_join_chain(digest, tables_found)
        if chain:
            join_path = chain[0]
            base_intent = f"{base_intent}_JOIN"

    # Criamos uma "assinatura" da query atual para comparar com as gravadas
    req_tables = set(tables_found)
    req_filters = {(f.field.lower(), f.op) for f in slots.filters}

    from app.services.semantic.enrichment_detector import detect_projection_expansion
    enrichment_detected = detect_projection_expansion(resolved_msg)
    if enrichment_detected:
        logger.info(f"[SEMANTIC_PATTERN_ENRICHMENT_DETECTED] Expansão de projeção detectada na mensagem.")

    # Busca os melhores patterns
    candidates = []

    for p in patterns:
        # FASE 2: Match exato de tabelas
        if set(p.tables) != req_tables:
            continue
            
        transformed_result = None
        if p.intent_family != base_intent:
            from app.services.semantic.pattern_transformer import can_transform, transform_pattern
            if can_transform(p, base_intent):
                transformed_result = transform_pattern(p, base_intent, slots, digest)
            
            if not transformed_result:
                continue

        # Match estrutural de filtros (na Fase 4 exigimos segurança rígida)
        pat_filters = {(f.field.lower(), f.op) for f in p.filters}
        
        # Só consideramos match se a estrutura de filtros exigida for identica à salva!
        if pat_filters != req_filters:
            continue

        # Avaliação Heurística do Candidato (FASE 4)
        cand = calculate_pattern_score(
            p, 
            is_transformed=bool(transformed_result), 
            full_filter_match=True,
            enrichment_detected=enrichment_detected
        )
        
        if cand.final_score <= 0.0:
            logger.warning(f"[SEMANTIC_PATTERN_REJECTED_PROJECTION_EXPANSION] Pattern {p.id} rejeitado: {cand.reasons[-1]}")
            continue

        cand.transformed_result = transformed_result
        candidates.append(cand)

    if not candidates:
        if enrichment_detected:
            logger.info("[SEMANTIC_PATTERN_REUSE_BLOCKED] Reuso bloqueado devido a pedido de enriquecimento estrutural.")
        else:
            logger.debug("[SEMANTIC_PATTERN_MISS] Nenhum padrão compatível encontrado.")
        return None
        
    logger.info(f"[SEMANTIC_PATTERN_CANDIDATES_FOUND] Encontrados {len(candidates)} candidatos.")
    
    ranked = rank_candidates(candidates)
    selected = should_auto_select(ranked)
    
    if not selected:
        return None

    best_pattern = selected.pattern
    best_transformed_result = selected.transformed_result

    logger.info(f"[SEMANTIC_PATTERN_SELECTED] Escolhido Padrão {best_pattern.id} (Score {selected.final_score:.2f}) para tabelas {best_pattern.tables}")
    
    # Mapear os valores atuais para os parâmetros (p0, p1...) do template
    params = {}
    if best_transformed_result:
        # FASE 3: Usamos integralmente a reconstrução 100% segura do query builder
        sql = best_transformed_result.sql
        params = best_transformed_result.params
        logger.info(f"[SEMANTIC_PATTERN_MODE_CHANGED] Transformado {best_pattern.intent_family} -> {base_intent}")
        logger.info(f"[SEMANTIC_PATTERN_SLOT_UPDATED] Slots reprocessados: {params}")
    else:
        # FASE 2: String template nativo com extração direta
        for mem_filter in best_pattern.filters:
            # Achar o slot correspondente na requisição atual
            for req_f in slots.filters:
                if req_f.field.lower() == mem_filter.field.lower() and req_f.op == mem_filter.op:
                    params[mem_filter.slot_name] = req_f.value
                    break
                    
        logger.info(f"[SEMANTIC_PATTERN_SLOT_EXTRACTED] Extraídos slots do usuário: {params}")

        sql = best_pattern.sql_template
        if slots.limit:
            sql = re.sub(r"LIMIT \d+", f"LIMIT {slots.limit}", sql, flags=re.IGNORECASE)

    logger.info(f"[SEMANTIC_PATTERN_EXECUTED] Executando query: {sql}")

    # Executar diretamente
    req = DBExecuteRequest(
        sql=sql,
        params=params, 
        mode="read",
        dry_run=False,
    )

    try:
        result = db_execute.execute(req, agent)
    except Exception as exc:
        logger.error(f"[SEMANTIC_MATCH] Erro na execução: {exc}")
        return None

    if not result.success:
        logger.warning(f"[SEMANTIC_PATTERN_FALLBACK] Execução falhou (erro: {result.error}), caindo no fallback")
        update_pattern_usage(agent_id, best_pattern.id, success=False)
        return None

    update_pattern_usage(agent_id, best_pattern.id, success=True)
    
    try:
        analytics_service.record_tables_mentioned(agent_id, best_pattern.tables)
        analytics_service.record_intent(agent_id, f"SEMANTIC_{best_pattern.intent_family}")
        if alias_hits:
            analytics_service.record_aliases_used(agent_id, alias_hits)
    except Exception:
        pass

    from types import SimpleNamespace
    mock_plan = SimpleNamespace(filters=slots.filters, limit=slots.limit)
    mock_build = SimpleNamespace(tables_used=best_pattern.tables, sql=sql)

    response_text = _format_response(base_intent, mock_build, result, mock_plan)

    return FastPathResult(
        intent=f"SEMANTIC_{base_intent}",
        response=response_text,
        sql=sql,
        table_name=", ".join(best_pattern.tables),
        rows=result.rows or [],
        status="completed",
        execution_source="semantic_transform" if best_transformed_result else "semantic_history",
        metadata={
            "pattern_id": best_pattern.id,
            "transformed": bool(best_transformed_result),
            "original_intent": best_pattern.intent_family,
            "final_intent": base_intent
        }
    )
