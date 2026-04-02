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

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.draft import AddDraftTableRequest, DiagramDraft, DraftTable

logger = get_logger("diagram_draft_service")


# ─── Caminhos ─────────────────────────────────────────────────────────────────

def _draft_path(agent_id: str) -> Path:
    return settings.drafts_path / f"{agent_id}.json"


# ─── API Pública ──────────────────────────────────────────────────────────────

def get_draft(agent_id: str) -> DiagramDraft:
    """Carrega o draft do agente. Retorna draft vazio se não existir."""
    path = _draft_path(agent_id)
    if not path.exists():
        return DiagramDraft(agent_id=agent_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DiagramDraft.model_validate(raw)
    except Exception as exc:
        logger.warning(f"[DRAFT] Erro ao carregar draft para '{agent_id}': {exc} — retornando vazio")
        return DiagramDraft(agent_id=agent_id)


def add_table(agent_id: str, request: AddDraftTableRequest) -> DraftTable:
    """
    Adiciona ou substitui uma tabela draft para o agente.
    Se já existe uma tabela com o mesmo nome, substitui.
    """
    draft = get_draft(agent_id)

    # Remover existente com mesmo nome (substituição)
    draft.draft_tables = [t for t in draft.draft_tables if t.name != request.name]

    new_table = DraftTable(
        name=request.name,
        columns=request.columns,
    )
    draft.draft_tables.append(new_table)
    draft.saved_at = datetime.now(timezone.utc)

    _persist(draft)
    logger.info(f"[DRAFT] Tabela draft adicionada: agente={agent_id} | tabela={request.name}")
    return new_table


def remove_table(agent_id: str, table_name: str) -> bool:
    """
    Remove uma tabela draft pelo nome.
    Retorna True se removida, False se não encontrada.
    """
    draft = get_draft(agent_id)
    before = len(draft.draft_tables)
    draft.draft_tables = [t for t in draft.draft_tables if t.name != table_name]
    if len(draft.draft_tables) == before:
        return False
    draft.saved_at = datetime.now(timezone.utc)
    _persist(draft)
    logger.info(f"[DRAFT] Tabela draft removida: agente={agent_id} | tabela={table_name}")
    return True


def promote_table(agent_id: str, table_name: str) -> bool:
    """
    'Promove' uma tabela draft — remove do draft após criação real no banco.
    Equivale funcionalmente a remove_table, mas com semântica explícita de promoção.
    """
    removed = remove_table(agent_id, table_name)
    if removed:
        logger.info(f"[DRAFT] Tabela promovida para real: agente={agent_id} | tabela={table_name}")
    return removed


def clear_all(agent_id: str) -> None:
    """Remove todos os drafts do agente."""
    path = _draft_path(agent_id)
    if path.exists():
        path.unlink()
    logger.info(f"[DRAFT] Todos os drafts removidos: agente={agent_id}")


# ─── Persistência ─────────────────────────────────────────────────────────────

def _persist(draft: DiagramDraft) -> None:
    path = _draft_path(draft.agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
        logger.debug(f"[DRAFT] Salvo: {path}")
    except Exception as exc:
        logger.error(f"[DRAFT] Erro ao salvar draft '{draft.agent_id}': {exc}")
        raise
