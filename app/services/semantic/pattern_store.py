import json
import os
import hashlib
from datetime import datetime
from typing import Optional

from app.core.logger import get_logger
from app.schemas.semantic import SemanticPattern, PatternFilter

logger = get_logger("semantic_pattern_store")

DATA_DIR = "data/semantic_patterns"

def _get_file_path(agent_id: str) -> str:
    return os.path.join(DATA_DIR, f"{agent_id}.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_patterns(agent_id: str) -> list[SemanticPattern]:
    """Carrega os patterns persistidos de um agente."""
    path = _get_file_path(agent_id)
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [SemanticPattern(**p) for p in data]
    except Exception as e:
        logger.error(f"Erro ao carregar patterns para {agent_id}: {e}")
        return []

def save_patterns(agent_id: str, patterns: list[SemanticPattern]):
    """Sobrescreve a lista de patterns do agente no arquivo JSON."""
    _ensure_dir()
    path = _get_file_path(agent_id)
    try:
        data = [p.model_dump(mode="json") for p in patterns]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Salvos {len(patterns)} patterns para {agent_id}")
    except Exception as e:
        logger.error(f"Erro ao salvar patterns para {agent_id}: {e}")

def list_patterns(agent_id: str) -> list[SemanticPattern]:
    """Alias para load_patterns"""
    return load_patterns(agent_id)

def generate_pattern_id(intent: str, tables: list[str], filters: list[PatternFilter]) -> str:
    """Gera um ID hash reprodutível baseado na estrutura de intenção."""
    sig = f"{intent}|{','.join(tables)}|"
    for f in filters:
        sig += f"{f.field}:{f.op}:{f.slot_name},"
    return "ptn_" + hashlib.md5(sig.encode()).hexdigest()[:12]

def save_pattern(
    agent_id: str, 
    intent_family: str, 
    tables: list[str], 
    filters: list[PatternFilter],
    sql_template: str,
    user_message: str,
    limit: Optional[int] = None,
    order_by: Optional[list[dict]] = None,
    join_path: Optional[dict] = None
) -> SemanticPattern:

    """
    Registra ou atualiza um padrão semântico a partir de uma query bem sucedida.
    """
    order_by = order_by or []
    
    # Gerar ID único para essa *assinatura estrutural*
    pattern_id = generate_pattern_id(intent_family, tables, filters)
    
    patterns = load_patterns(agent_id)
    existing_idx = next((i for i, p in enumerate(patterns) if p.id == pattern_id), None)
    
    examples = [{
        "user_message": user_message,
        "slot_values": { f.slot_name: f.slot_value for f in filters }
    }]

    if existing_idx is not None:
        # Padrão já existe: atualiza uso e mantém histórico 
        p = patterns[existing_idx]
        p.usage_count += 1
        p.success_count += 1
        p.updated_at = datetime.now()
        # Adiciona o exemplo se for novo (limita a 5 exemplos para não inchar o json)
        if not any(e.get("user_message") == user_message for e in p.examples):
            p.examples.append(examples[0])
            if len(p.examples) > 5:
                p.examples.pop(0)
        p.sql_template = sql_template  # Sobrescreve pelo template mais recente
        save_patterns(agent_id, patterns)
        logger.info(f"[SEMANTIC_PATTERN_SAVED] Atualizado padrão {pattern_id} para {agent_id}")
        return p

    # Novo padrão
    new_pattern = SemanticPattern(
        id=pattern_id,
        agent_id=agent_id,
        intent_family=intent_family,
        mode=intent_family.lower(), # ex: "select"
        tables=tables,
        filters=filters,
        order_by=order_by,
        limit=limit,
        join_path=join_path,
        sql_template=sql_template,
        examples=examples
    )
    patterns.append(new_pattern)
    save_patterns(agent_id, patterns)
    logger.info(f"[SEMANTIC_PATTERN_SAVED] Novo padrão {pattern_id} para {agent_id} registrado.")
    
    return new_pattern

def update_pattern_usage(agent_id: str, pattern_id: str, success: bool = True):
    """Atualiza as métricas de uso de um padrão semântico, incluindo sucesso, falha e recência."""
    patterns = load_patterns(agent_id)
    for p in patterns:
        if p.id == pattern_id:
            p.usage_count += 1
            if success:
                p.success_count += 1
            else:
                p.failure_count += 1
                
            p.updated_at = datetime.now()
            p.last_used_at = datetime.now()
            
            save_patterns(agent_id, patterns)
            logger.info(f"[SEMANTIC_PATTERN_STATS_UPDATED] Atributos atualizados (Success={success}) para o pattern {p.id}")
            return
