"""
Schemas para visualizacao estrutural de banco baseada em digest.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DiagramColumn(BaseModel):
    name: str
    type: str
    is_pk: bool = False
    is_fk: bool = False
    nullable: bool = True


class DiagramNode(BaseModel):
    id: str
    label: str
    node_type: Literal["table", "view", "draft"] = "table"
    table_type: str = "BASE TABLE"
    primary_key: list[str] = Field(default_factory=list)
    columns: list[DiagramColumn] = Field(default_factory=list)


class DiagramEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = "FK"
    fk_column: Optional[str] = None
    ref_column: Optional[str] = None
    constraint_name: Optional[str] = None
    relation_type: Literal["foreign_key", "related"] = "foreign_key"
    support_only: bool = False


class DiagramSummary(BaseModel):
    tables: int = 0
    views: int = 0
    drafts: int = 0
    nodes: int = 0
    edges: int = 0


class DiagramPayload(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None
    database: str
    generated_at: datetime
    summary: DiagramSummary = Field(default_factory=DiagramSummary)
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    has_drafts: bool = False


class DiagramStatus(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None
    exists: bool = False
    valid: bool = False
    message: str = ""
    database: Optional[str] = None
    generated_at: Optional[datetime] = None
    nodes: int = 0
    edges: int = 0
