"""
Camada de agentes no contexto do platform_db.
"""
from typing import Optional

from app.schemas.agent import AgentDetail, AgentSummary
from app.services import agent_service


async def list_platform_agents() -> list[AgentSummary]:
    """Lista agentes registrados pela plataforma."""

    return await agent_service.list_agents()


async def get_platform_agent(agent_id: str) -> Optional[AgentDetail]:
    """Retorna detalhes de um agente registrado pela plataforma."""

    return await agent_service.get_agent_detail(agent_id)
