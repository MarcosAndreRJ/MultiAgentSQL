"""
Rascunho de rotas para Agent Bindings.

IMPORTANTE: este arquivo apenas descreve rotas futuras e NÃO é registrado em main.py
para evitar conflitos com a IA que está fazendo a separacao de etapa 2.

As rotas abaixo fazem apenas leitura e usam os serviços da plataforma.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.platform.agent_bindings_service import (
    get_agent_llm_bindings,
    get_agent_database_bindings,
    get_agent_runtime_binding_summary,
    list_agent_runtime_binding_summaries,
    resolve_agent_llm_binding,
    create_or_update_agent_llm_binding,
    validate_agent_llm_binding,
)

router = APIRouter(prefix="/api/agents", tags=["agent-bindings"])


@router.get("/{agent_id}/llm-bindings")
async def api_get_agent_llm_bindings(agent_id: str, db: Session = Depends(get_db)):
    return {"llm_bindings": get_agent_llm_bindings(db, agent_id)}


@router.get("/{agent_id}/database-bindings")
async def api_get_agent_database_bindings(agent_id: str, db: Session = Depends(get_db)):
    return {"database_bindings": get_agent_database_bindings(db, agent_id)}


@router.get("/{agent_id}/llm-binding")
async def api_get_agent_llm_binding(agent_id: str, db: Session = Depends(get_db)):
    """Retorna o binding canônico (resolução) para um agente junto com validação."""
    resolved = resolve_agent_llm_binding(db, agent_id)
    return resolved


@router.put("/{agent_id}/llm-binding")
async def api_put_agent_llm_binding(agent_id: str, payload: dict, db: Session = Depends(get_db)):
    """Cria ou atualiza um binding LLM para o agente. Valida antes de persistir."""
    # Validate payload structure
    validation = validate_agent_llm_binding(db, payload)
    if not validation.get("is_valid"):
        raise HTTPException(status_code=400, detail={"errors": validation.get("errors")})

    try:
        binding = create_or_update_agent_llm_binding(db, agent_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"errors": [str(e)]})

    return {"binding_id": binding.id}


@router.get("/runtime-bindings/{agent_id}")
async def api_get_agent_runtime_binding(agent_id: str, db: Session = Depends(get_db)):
    s = get_agent_runtime_binding_summary(db, agent_id)
    if s is None:
        raise HTTPException(status_code=503, detail="Platform DB unavailable or summary not available")
    return s


@router.get("/runtime-bindings")
async def api_list_runtime_bindings(db: Session = Depends(get_db)):
    return {"summaries": list_agent_runtime_binding_summaries(db)}
