"""
Servico de diagrama:
- le digest salvo em disco
- transforma digest em estrutura de grafo para UI
- mescla tabelas reais (digest) com rascunhos visuais (drafts)

Fonte de verdade:
- data/digests/{agent_id}.digest.json  → tabelas/views reais + relacionamentos
- data/diagram_drafts/{agent_id}.json → tabelas de rascunho visual
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.diagram import (
    DiagramColumn,
    DiagramEdge,
    DiagramNode,
    DiagramPayload,
    DiagramStatus,
    DiagramSummary,
)
from app.schemas.digest import DBDigest, TableDigest
from app.schemas.draft import DiagramDraft, DraftTable
from app.services import digest_service, diagram_draft_service

logger = get_logger("diagram_service")


class DiagramDigestError(Exception):
    """Erro base de digest para visualizacao."""


class DiagramDigestNotFoundError(DiagramDigestError):
    """Digest nao encontrado."""


class DiagramDigestInvalidError(DiagramDigestError):
    """Digest encontrado, mas invalido."""


def _digest_path(agent_id: str) -> Path:
    return settings.digests_path / f"{agent_id}.digest.json"


def _drafts_path(agent_id: str) -> Path:
    return settings.data_path / "diagram_drafts" / f"{agent_id}.json"


def _load_digest(agent_id: str, db: Optional[Session] = None) -> DBDigest:
    digest = digest_service.load_digest(agent_id, db)
    if not digest:
        raise DiagramDigestNotFoundError(
            "Digest nao encontrado. Gere o digest antes de visualizar a estrutura."
        )
    return digest


def _load_draft(agent_id: str, db: Optional[Session] = None) -> DiagramDraft | None:
    return diagram_draft_service.get_draft(agent_id, db)


def _build_node_from_table(table: TableDigest) -> DiagramNode:
    primary_key = [table.primary_key] if table.primary_key else []
    fk_columns = {fk.column for fk in table.foreign_keys}
    pk_set = set(primary_key)

    columns = [
        DiagramColumn(
            name=col.name,
            type=col.type,
            is_pk=col.name in pk_set,
            is_fk=col.name in fk_columns,
            nullable=col.nullable,
        )
        for col in table.columns
    ]

    node_type = "view" if table.type.upper() == "VIEW" else "table"
    return DiagramNode(
        id=table.name,
        label=table.name,
        node_type=node_type,
        table_type=table.type,
        primary_key=primary_key,
        columns=columns,
    )


def _build_node_from_draft(draft_table: DraftTable) -> DiagramNode:
    columns = [
        DiagramColumn(
            name=col.name,
            type=col.sql_type,
            is_pk=col.pk,
            is_fk=False,
            nullable=col.nullable,
        )
        for col in draft_table.columns
    ]

    pk_cols = [col.name for col in draft_table.columns if col.pk]
    return DiagramNode(
        id=draft_table.name,
        label=draft_table.name,
        node_type="draft",
        table_type="DRAFT_TABLE",
        primary_key=pk_cols,
        columns=columns,
    )


def build_diagram(agent_id: str, agent_name: str | None = None, db: Optional[Session] = None) -> DiagramPayload:
    """
    Monta payload de diagrama mesclando:
    1. Tabelas/views reais do digest
    2. Relacionamentos reais do digest (n\u00E3o inferidos)
    3. Tabelas de rascunho visual do draft (se existirem)
    """
    digest = _load_digest(agent_id, db)
    draft = _load_draft(agent_id, db)

    # ── Nós reais ──────────────────────────────────────────────────────────────
    all_real_objects = list(digest.tables) + list(digest.views)
    nodes: list[DiagramNode] = [_build_node_from_table(t) for t in all_real_objects]
    node_ids = {node.id for node in nodes}

    # ── Nós de rascunho ────────────────────────────────────────────────────────
    draft_tables: list[DraftTable] = []
    if draft and draft.draft_tables:
        for dt in draft.draft_tables:
            if dt.name in node_ids:
                # Rascunho com mesmo nome que tabela real — ignorar draft
                logger.warning(
                    f"[DIAGRAM] Draft '{dt.name}' ignorado: já existe como tabela real no digest"
                )
                continue
            draft_node = _build_node_from_draft(dt)
            nodes.append(draft_node)
            node_ids.add(dt.name)
            draft_tables.append(dt)

    # ── Edges: fonte canônica = digest.relationships ───────────────────────────
    # Usa APENAS relacionamentos explícitos do banco (FKs reais).
    # Não inventa relacionamentos heurísticos.
    edges: list[DiagramEdge] = []
    seen_edge_ids: set[str] = set()

    for rel in digest.relationships:
        if rel.source_table not in node_ids or rel.target_table not in node_ids:
            # Uma das extremidades não está no diagrama atual (draft/filtro)
            continue

        edge_id = f"{rel.source_table}__{rel.target_table}__{rel.source_column}"
        if edge_id in seen_edge_ids:
            continue
        seen_edge_ids.add(edge_id)

        edges.append(
            DiagramEdge(
                id=edge_id,
                source=rel.source_table,
                target=rel.target_table,
                label=f"{rel.source_column} → {rel.target_table}.{rel.target_column}",
                fk_column=rel.source_column,
                ref_column=rel.target_column,
                constraint_name=rel.constraint_name,
                relation_type="foreign_key",
                support_only=False,
            )
        )

    # Compatibilidade retroativa: se o digest não tem relationships mas tem FKs
    # nas tabelas (digest gerado antes dessa versão), derivar edges das FKs.
    if not digest.relationships:
        logger.info("[DIAGRAM] digest sem relationships — derivando edges das FKs por tabela (legado)")
        unique_fk_keys: set[tuple[str, str, str, str, str]] = set()
        for table in all_real_objects:
            for fk in table.foreign_keys:
                if fk.ref_table not in node_ids:
                    continue
                key = (table.name, fk.ref_table, fk.column, fk.ref_column, fk.constraint_name)
                if key in unique_fk_keys:
                    continue
                unique_fk_keys.add(key)
                edge_id = f"{table.name}__{fk.ref_table}__{fk.column}"
                if edge_id not in seen_edge_ids:
                    seen_edge_ids.add(edge_id)
                    edges.append(
                        DiagramEdge(
                            id=edge_id,
                            source=table.name,
                            target=fk.ref_table,
                            label=f"{fk.column} → {fk.ref_table}.{fk.ref_column}",
                            fk_column=fk.column,
                            ref_column=fk.ref_column,
                            constraint_name=fk.constraint_name or None,
                            relation_type="foreign_key",
                            support_only=False,
                        )
                    )

    nodes.sort(key=lambda n: (n.node_type != "draft", n.label.lower()))
    edges.sort(key=lambda e: (e.source.lower(), e.target.lower(), e.fk_column or ""))

    has_drafts = len(draft_tables) > 0
    summary = DiagramSummary(
        tables=len(digest.tables),
        views=len(digest.views),
        drafts=len(draft_tables),
        nodes=len(nodes),
        edges=len(edges),
    )

    logger.info(
        f"[DIAGRAM] Payload montado | agente={agent_id} | "
        f"nodes={len(nodes)} | edges={len(edges)} | drafts={len(draft_tables)}"
    )

    return DiagramPayload(
        agent_id=digest.agent_id,
        agent_name=agent_name,
        database=digest.database,
        generated_at=digest.generated_at,
        summary=summary,
        nodes=nodes,
        edges=edges,
        has_drafts=has_drafts,
    )


def get_diagram_status(agent_id: str, agent_name: str | None = None, db: Optional[Session] = None) -> DiagramStatus:
    """
    Status do diagrama com base no digest salvo.
    Usa apenas leitura + parse do JSON sem construir o grafo completo.
    """
    try:
        digest = _load_digest(agent_id, db)
    except DiagramDigestNotFoundError:
        return DiagramStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            exists=False,
            valid=False,
            message="Digest n\u00E3o encontrado. Gere o digest antes de visualizar a estrutura.",
        )
    except DiagramDigestInvalidError as exc:
        logger.warning(f"[DIAGRAM] digest invalido para '{agent_id}': {exc}")
        return DiagramStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            exists=True,
            valid=False,
            message="Digest invalido. Gere o digest novamente antes de visualizar a estrutura.",
        )
    except DiagramDigestError as exc:
        logger.warning(f"[DIAGRAM] erro de digest para '{agent_id}': {exc}")
        return DiagramStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            exists=True,
            valid=False,
            message=str(exc),
        )
    except Exception as exc:
        logger.error(f"[DIAGRAM] erro inesperado ao ler digest para '{agent_id}': {exc}", exc_info=True)
        return DiagramStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            exists=True,
            valid=False,
            message="Falha ao ler digest para visualizacao da estrutura.",
        )

    total_tables = len(digest.tables)
    total_views = len(digest.views)
    # Usar relationships do nível raiz se disponível
    total_edges = len(digest.relationships) if digest.relationships else sum(
        len(t.foreign_keys) for t in digest.tables
    )

    msg = "Digest pronto para visualizacao."
    if total_edges == 0:
        msg = "Digest valido, sem relacionamentos detectados."

    return DiagramStatus(
        agent_id=agent_id,
        agent_name=agent_name,
        exists=True,
        valid=True,
        message=msg,
        database=digest.database,
        generated_at=digest.generated_at,
        nodes=total_tables + total_views,
        edges=total_edges,
    )

