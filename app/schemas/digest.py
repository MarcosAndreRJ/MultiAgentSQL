"""
Schemas Pydantic para DB Digest e Table Aliases.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Digest ────────────────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    comment: Optional[str] = None
    extra: Optional[str] = None


class ForeignKeyInfo(BaseModel):
    constraint_name: str
    column: str
    ref_table: str
    ref_column: str


class RelationshipInfo(BaseModel):
    """Relacionamento explícito entre duas tabelas, derivado de FK real do banco."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    constraint_name: str
    relationship_type: str = "many-to-one"  # sempre many-to-one para FKs simples


class TableDigest(BaseModel):
    name: str
    type: str = "BASE TABLE"  # ou "VIEW"
    primary_key: Optional[str] = None
    columns: list[ColumnInfo] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = Field(default_factory=list)
    related_tables: list[str] = Field(default_factory=list)
    description: str = ""
    row_count: Optional[int] = None


class TriggerDigest(BaseModel):
    name: str
    event: str = ""        # INSERT / UPDATE / DELETE
    timing: str = ""       # BEFORE / AFTER
    table: str = ""


class RoutineDigest(BaseModel):
    name: str
    type: str = ""         # PROCEDURE / FUNCTION


class DigestSummary(BaseModel):
    tables: int = 0
    views: int = 0
    triggers: int = 0
    procedures: int = 0
    functions: int = 0
    relationships: int = 0


class DBDigest(BaseModel):
    agent_id: str
    database: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: DigestSummary = Field(default_factory=DigestSummary)
    tables: list[TableDigest] = Field(default_factory=list)
    views: list[TableDigest] = Field(default_factory=list)
    triggers: list[TriggerDigest] = Field(default_factory=list)
    procedures: list[RoutineDigest] = Field(default_factory=list)
    functions: list[RoutineDigest] = Field(default_factory=list)
    relationships: list[RelationshipInfo] = Field(default_factory=list)


class DigestStatus(BaseModel):
    agent_id: str
    exists: bool
    generated_at: Optional[datetime] = None
    tables: int = 0
    views: int = 0
    triggers: int = 0
    procedures: int = 0
    functions: int = 0


# ─── Aliases ───────────────────────────────────────────────────────────────────

class AliasData(BaseModel):
    agent_id: str
    database: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    aliases: dict[str, str] = Field(default_factory=dict)
    manual_aliases: dict[str, str] = Field(default_factory=dict)


class ManualAliasRequest(BaseModel):
    alias: str = Field(..., description="Token com @, ex: @Hints")
    table_name: str = Field(..., description="Nome real da tabela")
