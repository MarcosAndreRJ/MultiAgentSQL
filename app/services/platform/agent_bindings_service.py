"""
Serviço de Plataforma: Gerencia Bindings (Vínculos) de Agentes.
Associa Agente ID -> Target DB e Agente ID -> LLM Config.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db import models
from app.core.logger import get_logger
from app.services.platform import platform_db_state

logger = get_logger("platform.agent_bindings")


def get_agent_llm_bindings(db: Session, agent_id: str) -> List[models.AgentLLMBinding]:
    """Compat wrapper para listagem de bindings LLM."""
    return list_agent_llm_bindings(db, agent_id)



def get_agent_runtime_binding_summary(db: Session, agent_id: str) -> Optional[dict]:
    """Resumo mínimo de bindings ativos por agente (compatibilidade de rota rascunho)."""
    if not platform_db_state.is_platform_db_connected():
        return None

    llm_default = get_agent_primary_llm(db, agent_id)
    
    from app.services.platform.agent_database_binding_service import resolve_agent_database_binding
    target_default = None
    try:
        target_default = resolve_agent_database_binding(db, agent_id)
    except ValueError:
        pass

    status = "ok" if (llm_default is not None or target_default is not None) else "empty"

    return {
        "agent_id": agent_id,
        "llm_binding": llm_default,
        "target_db_binding": target_default,
        "has_default_llm_binding": llm_default is not None,
        "has_default_target_db_binding": target_default is not None,
        "status": status,
    }


def list_agent_runtime_binding_summaries(db: Session) -> List[dict]:
    """Lista resumos de runtime para agentes com qualquer tipo de binding."""
    if not platform_db_state.is_platform_db_connected():
        return []

    agent_ids = set()
    for row in db.query(models.AgentLLMBinding.agent_id).distinct().all():
        agent_ids.add(row[0])
    for row in db.query(models.AgentDatabaseBindingV2.agent_id).distinct().all():
        agent_ids.add(row[0])

    return [get_agent_runtime_binding_summary(db, aid) for aid in sorted(agent_ids)]



def list_agent_llm_bindings(db: Session, agent_id: str) -> List[models.AgentLLMBinding]:
    """
    Lista todos os modelos LLM vinculados a um agente.
    """
    if not platform_db_state.is_platform_db_connected():
        return []

    return db.query(models.AgentLLMBinding).filter(
        models.AgentLLMBinding.agent_id == agent_id
    ).order_by(models.AgentLLMBinding.fallback_order.asc()).all()

def get_agent_primary_llm(db: Session, agent_id: str) -> Optional[models.AgentLLMBinding]:
    """
    Retorna o modelo LLM primário (default) de um agente.
    """
    if not platform_db_state.is_platform_db_connected():
        return None

    return db.query(models.AgentLLMBinding).filter(
        models.AgentLLMBinding.agent_id == agent_id,
        models.AgentLLMBinding.is_default == True
    ).first()



def get_agent_llm_binding(db: Session, agent_id: str) -> Optional[models.AgentLLMBinding]:
    """
    Retorna um único binding primário (is_default True) ou o primeiro ativo para o agente.
    """
    if not platform_db_state.is_platform_db_connected():
        return None

    return db.query(models.AgentLLMBinding).filter(
        models.AgentLLMBinding.agent_id == agent_id,
        models.AgentLLMBinding.is_active == True
    ).order_by(models.AgentLLMBinding.is_default.desc(), models.AgentLLMBinding.fallback_order.asc()).first()


def validate_agent_llm_binding(db: Session, binding_payload: dict) -> dict:
    """
    Valida as regras de governança para um payload de binding LLM. Retorna um dicionário com
    is_valid: bool e errors: list[str]. Não persiste nada.
    """
    errors = []
    if not platform_db_state.is_platform_db_connected():
        return {"is_valid": False, "errors": ["Platform DB is not connected"]}

    provider_id = binding_payload.get("provider_id")
    model_id = binding_payload.get("model_id")
    fallback_provider_id = binding_payload.get("fallback_provider_id")
    fallback_model_id = binding_payload.get("fallback_model_id")
    require_tools = binding_payload.get("supports_tools_required") or False
    require_json = binding_payload.get("supports_json_required") or False
    require_streaming = binding_payload.get("require_streaming") or False
    min_context = binding_payload.get("min_context_window")

    # Basic existence checks
    provider = db.query(models.LLMProvider).filter(models.LLMProvider.id == provider_id).first() if provider_id else None
    if provider is None:
        errors.append("provider_id does not reference an existing provider")
    else:
        if not provider.is_active:
            errors.append("provider is not active")

    model = db.query(models.LLMModel).filter(models.LLMModel.id == model_id).first() if model_id else None
    if model is None:
        errors.append("model_id does not reference an existing model")
    else:
        if not model.is_active or not model.is_available:
            errors.append("model is not active/available")

    # model must belong to provider
    if provider and model and model.provider_id != provider.id:
        errors.append("model does not belong to the specified provider")

    # capability checks
    if require_tools and model and not model.supports_tools:
        errors.append("model does not support tools but tools are required")
    if require_json and model and not model.supports_json:
        errors.append("model does not support json but json is required")
    if require_streaming and model and not model.supports_streaming:
        errors.append("model does not support streaming but streaming is required")
    if min_context is not None and model and model.context_window is not None and model.context_window < int(min_context):
        errors.append("model context window is smaller than the required min_context_window")

    # fallback validation (if provided)
    # Require both fallback_provider_id and fallback_model_id together for coherence.
    if (fallback_provider_id is not None) ^ (fallback_model_id is not None):
        errors.append("both fallback_provider_id and fallback_model_id must be provided together")
    elif fallback_provider_id is not None and fallback_model_id is not None:
        fp = db.query(models.LLMProvider).filter(models.LLMProvider.id == fallback_provider_id).first()
        fm = db.query(models.LLMModel).filter(models.LLMModel.id == fallback_model_id).first()
        if fp is None:
            errors.append("fallback_provider_id does not reference an existing provider")
        if fm is None:
            errors.append("fallback_model_id does not reference an existing model")
        if fp and fm and fm.provider_id != fp.id:
            errors.append("fallback model does not belong to the fallback provider")

    return {"is_valid": len(errors) == 0, "errors": errors}


def create_or_update_agent_llm_binding(db: Session, agent_id: str, binding_payload: dict) -> models.AgentLLMBinding:
    """
    Cria ou atualiza (upsert) o binding LLM para um agente. Valida antes de persistir e lança
    ValueError com detalhes em caso de erro de validação.
    """
    validation = validate_agent_llm_binding(db, binding_payload)
    if not validation.get("is_valid"):
        raise ValueError("; ".join(validation.get("errors", [])))

    # Ensure only one default binding per agent: if the incoming payload marks this
    # binding as default, clear the is_default flag from other bindings for the same agent.
    if binding_payload.get("is_default"):
        # Use a bulk update to clear previous defaults; synchronize_session=False for simplicity.
        db.query(models.AgentLLMBinding).filter(models.AgentLLMBinding.agent_id == agent_id).update({models.AgentLLMBinding.is_default: False}, synchronize_session=False)

    # Find existing binding with same agent/provider/model
    binding = db.query(models.AgentLLMBinding).filter(
        models.AgentLLMBinding.agent_id == agent_id,
        models.AgentLLMBinding.provider_id == binding_payload.get("provider_id"),
        models.AgentLLMBinding.model_id == binding_payload.get("model_id")
    ).first()

    if binding is None:
        binding = models.AgentLLMBinding(agent_id=agent_id, **binding_payload)
        db.add(binding)
    else:
        # update fields
        for k, v in binding_payload.items():
            setattr(binding, k, v)

    db.commit()
    db.refresh(binding)
    logger.info(f"Agent LLM binding saved | agent={agent_id} | provider={binding.provider_id} | model={binding.model_id}")
    return binding


def resolve_agent_llm_binding(db: Session, agent_id: str) -> dict:
    """
    Resolve o binding canônico para um agente aplicando validações e fallbacks.
    Retorna um dicionário com: agent_id, binding (or None), is_valid, validation_errors, source
    """
    if not platform_db_state.is_platform_db_connected():
        return {"agent_id": agent_id, "binding": None, "is_valid": False, "validation_errors": ["Platform DB offline"], "source": "none"}

    binding = get_agent_llm_binding(db, agent_id)
    if binding is None:
        # No DB binding; mark as legacy (yaml) resolve not implemented here
        return {"agent_id": agent_id, "binding": None, "is_valid": False, "validation_errors": ["no binding found"], "source": "none"}

    # Prepare payload for validation
    payload = {
        "provider_id": binding.provider_id,
        "model_id": binding.model_id,
        "fallback_provider_id": getattr(binding, "fallback_provider_id", None),
        "fallback_model_id": getattr(binding, "fallback_model_id", None),
        "supports_tools_required": binding.supports_tools_required,
        "supports_json_required": binding.supports_json_required,
        "require_streaming": getattr(binding, "require_streaming", False),
        "min_context_window": getattr(binding, "min_context_window", None),
    }

    validation = validate_agent_llm_binding(db, payload)

    return {
        "agent_id": agent_id,
        "binding": binding,
        "is_valid": validation.get("is_valid"),
        "validation_errors": validation.get("errors"),
        "source": "platform_db",
    }
