"""
Agent Service: operações sobre agentes (listagem, detalhes, status de conexão).
"""
from typing import Optional

from app.core import agent_registry
from app.core.logger import get_logger
from app.schemas.agent import AgentSummary, AgentDetail
from app.tools.db_connection_manager import test_connection

logger = get_logger("agent_service")


async def list_agents() -> list[AgentSummary]:
    """Lista todos os agentes com informações resumidas."""
    agents = agent_registry.get_all()
    summaries = []
    
    for config in agents:
        summary = AgentSummary(
            id=config.id,
            name=config.name,
            description=config.description,
            type=config.type,
            model=config.model,
            database_name=config.database.name if config.database else None,
            skills=config.skills,
            is_online=True,  # Ollama check pode ser feito em separado
        )
        summaries.append(summary)
    
    return summaries


async def get_agent_detail(agent_id: str) -> Optional[AgentDetail]:
    """Retorna detalhes completos de um agente."""
    config = agent_registry.get(agent_id)
    if not config:
        return None

    # Carregar preview do prompt
    from app.agents.prompt_builder import load_base_prompt
    try:
        prompt_preview = load_base_prompt(config)[:500] + "..." if len(load_base_prompt(config)) > 500 else load_base_prompt(config)
    except Exception:
        prompt_preview = None

    return AgentDetail(
        id=config.id,
        name=config.name,
        description=config.description,
        type=config.type,
        model=config.model,
        database_name=config.database.name if config.database else None,
        skills=config.skills,
        is_online=True,
        prompt_preview=prompt_preview,
        permissions=config.permissions,
        guards=config.guards,
        behavior=config.behavior,
    )


async def test_agent_connection(agent_id: str) -> dict:
    """Testa a conexão MySQL de um agente especialista."""
    config = agent_registry.get(agent_id)
    if not config:
        return {"success": False, "message": f"Agente '{agent_id}' não encontrado"}
    
    if not config.database:
        return {"success": False, "message": "Agente não possui banco de dados configurado"}
    
    success, message = test_connection(config.database)
    return {"success": success, "message": message, "agent_id": agent_id}
