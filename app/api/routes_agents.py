"""
API Routes: Agents
GET /api/agents - listar agentes
GET /api/agents/{agent_id} - detalhar agente
GET /api/agents/{agent_id}/test-connection - testar conexão
POST /api/agents/reload - recarregar agentes
"""
from fastapi import APIRouter, HTTPException

from app.services import agent_service
from app.services.chat_service import reload_agents

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/")
async def list_agents():
    """Lista todos os agentes configurados."""
    return await agent_service.list_agents()


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Detalhes de um agente específico."""
    agent = await agent_service.get_agent_detail(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    return agent


@router.get("/{agent_id}/test-connection")
async def test_connection(agent_id: str):
    """Testa a conexão MySQL do agente."""
    return await agent_service.test_agent_connection(agent_id)


@router.post("/reload")
async def reload():
    """Recarrega todos os agentes dos arquivos YAML."""
    reload_agents()
    return {"status": "ok", "message": "Agentes recarregados"}
