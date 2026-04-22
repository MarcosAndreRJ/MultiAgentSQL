"""
API Routes: Agents
GET /api/agents - listar agentes
GET /api/agents/{agent_id} - detalhar agente
GET /api/agents/{agent_id}/test-connection - testar conexão
POST /api/agents/reload - recarregar agentes
POST /api/agents - criar novo agente
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.services import agent_service
from app.services.chat_service import reload_agents, clear_agent_cache
from app.services.platform import agent_governance_service
from app.services.target_db import query_service
from app.schemas.agent import AgentCreate, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentQueryRequest(BaseModel):
    query: str


@router.post("", response_model=dict)
async def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    """Cria um novo agente."""
    try:
        agent = await agent_service.create_agent(payload, db)
        return {"ok": True, "agent": agent}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_agents():
    """Lista todos os agentes configurados."""
    agents = await agent_service.list_agents()
    return {"agents": agents}


@router.put("/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)):
    """Atualiza as configurações de um agente."""
    try:
        agents = await agent_service.update_agent(agent_id, payload, db)
        # Limpar cache de instância para forçar re-resolução do modelo LLM
        clear_agent_cache(agent_id)
        return {"ok": True, "agents": agents}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Detalhes de um agente específico."""
    agent = await agent_service.get_agent_detail(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    return {"ok": True, "agent": agent}


@router.get("/{agent_id}/test-connection")
async def test_connection(agent_id: str):
    """Testa a conexão MySQL do agente."""
    return await agent_service.test_agent_target_db_connection(agent_id)


@router.post("/reload")
async def reload():
    """Recarrega todos os agentes dos arquivos YAML."""
    reload_agents()
    return {"status": "ok", "message": "Agentes recarregados"}


@router.post("/{agent_id}/query")
async def execute_agent_query(agent_id: str, payload: AgentQueryRequest):
    """
    Executa query SQL read-only no target_db resolvendo binding ativo do agente.

    Regras:
    - não usa credenciais vindas do frontend
    - resolve `agent_database_binding` ativo no platform_db
    - mantém bloqueio de DDL/DML
    """
    try:
        result = query_service.execute_read_query(agent_id=agent_id, raw_query=payload.query)
        return {
            "status": result.get("status", "success"),
            "execution_id": result.get("execution_id"),
            "rows": result.get("rows", []),
            "execution_time_ms": result.get("execution_time_ms", 0),
        }
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na execução SQL: {str(e)}")


@router.get("/governance/list")
async def list_governance_agents(db: Session = Depends(get_db)):
    """Lista todos os agentes e seus status de governança no banco."""
    from app.db import models as db_models
    agents = db.query(db_models.Agent).all()
    return agents


@router.post("/{agent_id}/toggle")
async def toggle_agent_status(agent_id: str, db: Session = Depends(get_db)):
    """Inverte o status is_active de um agente."""
    from app.db import models as db_models
    agent = db.query(db_models.Agent).filter(db_models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado no banco de governança.")
    
    agent.is_active = not agent.is_active
    db.commit()
    # Limpar cache de instâncias para forçar re-resolução
    reload_agents()
    
    return {"ok": True, "agent_id": agent_id, "is_active": agent.is_active}


@router.post("/governance/sync-all")
async def sync_agents_from_yaml(db: Session = Depends(get_db)):
    """Sincroniza agentes do YAML para o banco (bootstrap manual)."""
    stats = agent_governance_service.bootstrap_governance_from_yaml(db)
    return {"ok": True, "stats": stats}
