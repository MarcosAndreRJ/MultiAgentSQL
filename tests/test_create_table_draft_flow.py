"""
Tests: fluxo completo criar tabela draft → aparece no payload → promover

Verifica o ciclo de vida de uma tabela draft:
1. Adicionar draft → aparece em get_draft
2. build_diagram inclui nó com node_type="draft"
3. has_drafts=True no payload
4. Após promote → não aparece mais no payload
5. Draft com mesmo nome de tabela real é ignorado no diagrama
"""
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.schemas.digest import DBDigest, DigestSummary, TableDigest
from app.schemas.draft import AddDraftTableRequest, DraftColumn
from app.services import diagram_draft_service
from app.services.diagram_service import build_diagram


# ── Helpers ────────────────────────────────────────────────────────────────────

def _empty_digest(agent_id: str = "agent-flow") -> DBDigest:
    return DBDigest(
        agent_id=agent_id,
        database="test_db",
        generated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        summary=DigestSummary(),
        tables=[TableDigest(name="TabelaReal", type="BASE TABLE")],
    )


def _persist_digest(tmp_path: Path, digest: DBDigest) -> None:
    d = tmp_path / "digests"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{digest.agent_id}.digest.json").write_text(
        digest.model_dump_json(), encoding="utf-8"
    )


def _patch_all(tmp_path: Path):
    """
    Patcher unificado para diagram_service e draft_service.

    diagram_service._drafts_path = settings.data_path / "diagram_drafts" / {id}.json
    diagram_draft_service._draft_path = settings.drafts_path / {id}.json

    Para que ambos escrevam/leiam do mesmo lugar:
        drafts_path  = tmp_path / "diagram_drafts"   (= data_path / "diagram_drafts")
    """
    import app.services.diagram_service as diag_svc
    import app.services.diagram_draft_service as draft_svc

    mock = MagicMock()
    mock.digests_path = tmp_path / "digests"
    mock.data_path = tmp_path
    mock.drafts_path = tmp_path / "diagram_drafts"  # mesmo subdir que diagram_service usa

    return (
        patch.object(diag_svc, "settings", mock),
        patch.object(draft_svc, "settings", mock),
    )


# ── Testes ─────────────────────────────────────────────────────────────────────

def test_draft_appears_in_diagram_payload(tmp_path):
    digest = _empty_digest()
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        # Adicionar draft
        req = AddDraftTableRequest(
            name="NovaTabela",
            columns=[DraftColumn(name="id", sql_type="INT", pk=True, nullable=False)],
        )
        diagram_draft_service.add_table("agent-flow", req)

        payload = build_diagram("agent-flow")

    node_ids = {n.id for n in payload.nodes}
    assert "NovaTabela" in node_ids
    draft_nodes = [n for n in payload.nodes if n.node_type == "draft"]
    assert len(draft_nodes) == 1
    assert draft_nodes[0].id == "NovaTabela"


def test_has_drafts_flag_set_when_drafts_present(tmp_path):
    digest = _empty_digest()
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        diagram_draft_service.add_table(
            "agent-flow",
            AddDraftTableRequest(
                name="DraftExtra",
                columns=[DraftColumn(name="col", sql_type="TEXT")],
            ),
        )
        payload = build_diagram("agent-flow")

    assert payload.has_drafts is True
    assert payload.summary.drafts == 1


def test_has_drafts_false_when_no_drafts(tmp_path):
    digest = _empty_digest()
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        payload = build_diagram("agent-flow")

    assert payload.has_drafts is False
    assert payload.summary.drafts == 0


def test_promote_removes_draft_from_diagram(tmp_path):
    digest = _empty_digest()
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        # Adicionar draft
        diagram_draft_service.add_table(
            "agent-flow",
            AddDraftTableRequest(
                name="TabPromover",
                columns=[DraftColumn(name="x", sql_type="INT")],
            ),
        )
        # Promover (equivale a remoção do draft)
        diagram_draft_service.promote_table("agent-flow", "TabPromover")

        payload = build_diagram("agent-flow")

    node_ids = {n.id for n in payload.nodes}
    assert "TabPromover" not in node_ids
    assert payload.has_drafts is False


def test_draft_with_same_name_as_real_table_is_ignored(tmp_path):
    """Draft com nome idêntico a tabela real não deve aparecer como nó draft."""
    digest = _empty_digest()  # tem "TabelaReal" como tabela real
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        diagram_draft_service.add_table(
            "agent-flow",
            AddDraftTableRequest(
                name="TabelaReal",  # mesmo nome de tabela real
                columns=[DraftColumn(name="col", sql_type="TEXT")],
            ),
        )
        payload = build_diagram("agent-flow")

    # Deve ter exatamente 1 nó "TabelaReal" (o real, não o draft)
    nodes_with_name = [n for n in payload.nodes if n.id == "TabelaReal"]
    assert len(nodes_with_name) == 1
    assert nodes_with_name[0].node_type == "table"
    assert payload.has_drafts is False


def test_multiple_drafts_all_appear_in_payload(tmp_path):
    digest = _empty_digest()
    _persist_digest(tmp_path, digest)

    p1, p2 = _patch_all(tmp_path)
    with p1, p2:
        for name in ["DraftA", "DraftB", "DraftC"]:
            diagram_draft_service.add_table(
                "agent-flow",
                AddDraftTableRequest(
                    name=name,
                    columns=[DraftColumn(name="id", sql_type="INT")],
                ),
            )
        payload = build_diagram("agent-flow")

    draft_nodes = [n for n in payload.nodes if n.node_type == "draft"]
    assert len(draft_nodes) == 3
    assert payload.summary.drafts == 3
