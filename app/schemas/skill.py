"""
Schemas para skills dos agentes.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Informações sobre uma skill."""
    id: str                    # Nome/slug da skill (ex: "mysql-defaults")
    filename: str              # Nome do arquivo .md
    title: str                 # Título extraído do .md
    description: Optional[str] = None
    content: Optional[str] = None   # Conteúdo completo (quando solicitado)
    size_bytes: int = 0
    last_modified: Optional[datetime] = None


class SkillAssign(BaseModel):
    """Payload para atribuir skill a um agente."""
    agent_id: str
    skill_id: str


class SkillRemove(BaseModel):
    """Payload para remover skill de um agente."""
    agent_id: str
    skill_id: str


class SkillList(BaseModel):
    """Lista de skills disponíveis."""
    skills: list[SkillInfo] = Field(default_factory=list)
    total: int = 0
