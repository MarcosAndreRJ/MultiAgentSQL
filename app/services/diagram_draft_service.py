"""
Diagram Draft Service — gerencia tabelas de rascunho visual do ERD.

Rascunhos vivem SEPARADOS do digest real e do banco de dados.
Permitem criar tabelas só no diagrama, depois promovê-las para o banco.

Armazenamento: data/diagram_drafts/{agent_id}.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.draft import AddDraftTableRequest, DiagramDraft, DraftTable
from app.db.models import AgentDiagramDraft

logger = get_logger("diagram_draft_service")


# ─── Caminhos ─────────────────────────────────────────────────────────────────

def _draft_path(agent_id: str) -> Path:
    return settings.drafts_path / f"{agent_id}.json"


# ─── API Pública ──────────────────────────────────────────────────────────────

def get_draft(agent_id: str, db: Optional[Session] = None) -> DiagramDraft:
    """Carrega o draft do agente do banco (prioridade) ou disco (fallback)."""
    # 1. Tenta carregar do banco
    if db:
        draft = _load_from_db(agent_id, db)
        if draft:
            return draft

    # 2. Fallback para disco
    path = _draft_path(agent_id)
    if not path.exists():
        return DiagramDraft(agent_id=agent_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DiagramDraft.model_validate(raw)
    except Exception as exc:
        logger.warning(f"[DRAFT] Erro ao carregar draft para '{agent_id}': {exc} — retornando vazio")
        return DiagramDraft(agent_id=agent_id)


def add_table(agent_id: str, request: AddDraftTableRequest, db: Optional[Session] = None) -> DraftTable:
    """
    Adiciona ou substitui uma tabela draft para o agente.
    Se já existe uma tabela com o mesmo nome, substitui.
    """
    draft = get_draft(agent_id, db)

    # Remover existente com mesmo nome (substituição)
    draft.draft_tables = [t for t in draft.draft_tables if t.name != request.name]

    new_table = DraftTable(
        name=request.name,
        columns=request.columns,
    )
    draft.draft_tables.append(new_table)
    draft.saved_at = datetime.now(timezone.utc)

    _persist(draft)
    if db:
        _persist_to_db(draft, db)
    logger.info(f"[DRAFT] Tabela draft adicionada: agente={agent_id} | tabela={request.name}")
    return new_table


def remove_table(agent_id: str, table_name: str, db: Optional[Session] = None) -> bool:
    """
    Remove uma tabela draft pelo nome.
    Retorna True se removida, False se não encontrada.
    """
    draft = get_draft(agent_id, db)
    before = len(draft.draft_tables)
    draft.draft_tables = [t for t in draft.draft_tables if t.name != table_name]
    if len(draft.draft_tables) == before:
        return False
    draft.saved_at = datetime.now(timezone.utc)
    _persist(draft)
    if db:
        _persist_to_db(draft, db)
    logger.info(f"[DRAFT] Tabela draft removida: agente={agent_id} | tabela={table_name}")
    return True


def promote_table(agent_id: str, table_name: str, db: Optional[Session] = None) -> bool:
    """
    'Promove' uma tabela draft — remove do draft após criação real no banco.
    Equivale funcionalmente a remove_table, mas com sem\u00E2ntica explícita de promo\u00E7\u00E3o.
    """
    removed = remove_table(agent_id, table_name, db)
    if removed:
        logger.info(f"[DRAFT] Tabela promovida para real: agente={agent_id} | tabela={table_name}")
    return removed


def clear_all(agent_id: str, db: Optional[Session] = None) -> None:
    """Remove todos os drafts do agente."""
    if db:
        _delete_from_db(agent_id, db)
    
    path = _draft_path(agent_id)
    if path.exists():
        path.unlink()
    logger.info(f"[DRAFT] Todos os drafts removidos: agente={agent_id}")


# ─── Persist\u00EAncia ─────────────────────────────────────────────────────────────

def _persist_to_db(draft: DiagramDraft, db: Session) -> None:
    """Persiste o rascunho visual no banco MySQL."""
    try:
        record = db.query(AgentDiagramDraft).filter(AgentDiagramDraft.agent_id == draft.agent_id).first()
        draft_json = draft.model_dump_json()

        if record:
            record.draft_json = draft_json
        else:
            record = AgentDiagramDraft(
                agent_id=draft.agent_id,
                draft_json=draft_json
            )
            db.add(record)
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[DRAFT] Erro ao persistir no banco: {e}")

def _load_from_db(agent_id: str, db: Session) -> Optional[DiagramDraft]:
    """Carrega o rascunho visual do banco MySQL."""
    try:
        record = db.query(AgentDiagramDraft).filter(AgentDiagramDraft.agent_id == agent_id).first()
        if record:
            data = json.loads(record.draft_json)
            return DiagramDraft.model_validate(data)
    except Exception as e:
        logger.error(f"[DRAFT] Erro ao carregar do banco '{agent_id}': {e}")
    return None

def _delete_from_db(agent_id: str, db: Session) -> None:
    """Remove o rascunho do banco MySQL."""
    try:
        db.query(AgentDiagramDraft).filter(AgentDiagramDraft.agent_id == agent_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[DRAFT] Erro ao remover do banco '{agent_id}': {e}")

def _persist(draft: DiagramDraft) -> None:
    path = _draft_path(draft.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
        logger.debug(f"[DRAFT] Salvo: {path}")
    except Exception as exc:
        logger.error(f"[DRAFT] Erro ao salvar draft '{draft.agent_id}': {exc}")
        raise
