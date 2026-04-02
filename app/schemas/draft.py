"""
Schemas para tabelas de rascunho (draft) do ERD.

Drafts são objetos visuais temporários criados apenas no ERD, que ainda não
existem no banco de dados real. Ficam separados do digest para nunca confundir
modelo real com modelo em rascunho.

Armazenados em: data/diagram_drafts/{agent_id}.json
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DraftColumn(BaseModel):
    """Definição de uma coluna de tabela draft."""
    name: str
    sql_type: str = "VARCHAR(255)"
    pk: bool = False
    nullable: bool = True
    auto_increment: bool = False
    default_val: Optional[str] = None


class DraftTable(BaseModel):
    """Tabela que existe apenas no ERD (rascunho visual)."""
    name: str
    type: str = "DRAFT_TABLE"
    columns: list[DraftColumn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiagramDraft(BaseModel):
    """Conjunto de objetos de rascunho para um agente."""
    agent_id: str
    saved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    draft_tables: list[DraftTable] = Field(default_factory=list)
    # Relacionamentos entre drafts (reservado para uso futuro)
    draft_relationships: list[dict] = Field(default_factory=list)


class AddDraftTableRequest(BaseModel):
    """Payload para criar/adicionar uma tabela draft."""
    name: str
    columns: list[DraftColumn] = Field(default_factory=list)
