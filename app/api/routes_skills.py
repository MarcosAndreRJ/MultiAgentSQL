"""
API Routes: Skills
GET /api/skills - listar todas as skills disponíveis
GET /api/skills/{skill_id} - detalhes de uma skill
POST /api/agents/{agent_id}/skills - adicionar skill ao agente
DELETE /api/agents/{agent_id}/skills/{skill_id} - remover skill do agente
"""
from fastapi import APIRouter, HTTPException

from app.agents.skill_loader import list_available_skills, get_skill_content
from app.core import agent_registry
from app.core.logger import get_logger

router = APIRouter(tags=["skills"])
logger = get_logger("routes_skills")


@router.get("/api/skills/")
async def list_skills():
    """Lista todas as skills disponíveis."""
    skills = list_available_skills()
    return {"skills": skills, "total": len(skills)}


@router.get("/api/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Retorna conteúdo completo de uma skill."""
    skill = get_skill_content(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' não encontrada")
    return skill


@router.post("/api/agents/{agent_id}/skills")
async def add_skill(agent_id: str, skill_id: str):
    """Adiciona uma skill a um agente (em memória, sem persistir no YAML)."""
    if not agent_registry.exists(agent_id):
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    
    # Verificar se a skill existe
    skill = get_skill_content(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' não encontrada")
    
    success = agent_registry.add_skill_to_agent(agent_id, skill_id)
    return {"status": "ok" if success else "error", "agent_id": agent_id, "skill_id": skill_id}


@router.delete("/api/agents/{agent_id}/skills/{skill_id}")
async def remove_skill(agent_id: str, skill_id: str):
    """Remove uma skill de um agente."""
    if not agent_registry.exists(agent_id):
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado")
    
    success = agent_registry.remove_skill_from_agent(agent_id, skill_id)
    return {"status": "ok" if success else "error", "agent_id": agent_id, "skill_id": skill_id}
